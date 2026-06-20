//! RingBuffer: a comptime-generic, fixed-capacity FIFO (circular buffer).
//!
//! Where `DynArray` grows on demand, `RingBuffer` is bounded: its capacity is
//! chosen once at construction and never changes. That makes it a good second
//! example of the same SIGNATURE features used in a different shape:
//!
//!   * comptime generics  -> `RingBuffer(comptime T: type)` returns a type.
//!   * explicit allocator  -> `init` takes the allocator that owns the buffer;
//!                            `deinit` returns it. The allocator is *not* stored.
//!   * error sets          -> `push` returns `error{BufferFull}` when full;
//!                            `init` returns `Allocator.Error`.
//!   * optionals           -> `pop`/`peek` return `?T` (empty -> null).
//!   * slices              -> backing storage is a `[]T` slice; `copyToSlice`
//!                            drains into a caller-provided `[]T`.
//!
//! The classic ring-buffer trick: a `head` index, a `len`, and modular
//! arithmetic. `tail = (head + len) % cap`. No element shifting on pop.

const std = @import("std");
const Allocator = std.mem.Allocator;

/// Error returned when pushing onto a full buffer. A one-member error set keeps
/// the failure precise and lets callers `catch` exactly this case.
pub const PushError = error{BufferFull};

pub fn RingBuffer(comptime T: type) type {
    return struct {
        const Self = @This();

        buffer: []T,
        head: usize,
        len: usize,

        /// Allocate a buffer of exactly `cap` elements. `cap` must be > 0.
        pub fn init(gpa: Allocator, cap: usize) Allocator.Error!Self {
            std.debug.assert(cap > 0);
            return .{
                .buffer = try gpa.alloc(T, cap),
                .head = 0,
                .len = 0,
            };
        }

        /// Free the backing buffer with the same allocator passed to `init`.
        pub fn deinit(self: *Self, gpa: Allocator) void {
            gpa.free(self.buffer);
            self.* = undefined;
        }

        pub fn capacity(self: Self) usize {
            return self.buffer.len;
        }

        pub fn count(self: Self) usize {
            return self.len;
        }

        pub fn isEmpty(self: Self) bool {
            return self.len == 0;
        }

        pub fn isFull(self: Self) bool {
            return self.len == self.buffer.len;
        }

        /// Enqueue at the tail. Returns `error.BufferFull` if no room — the
        /// caller decides whether that is fatal (try) or expected (catch).
        pub fn push(self: *Self, value: T) PushError!void {
            if (self.isFull()) return error.BufferFull;
            const tail = (self.head + self.len) % self.buffer.len;
            self.buffer[tail] = value;
            self.len += 1;
        }

        /// Enqueue, overwriting the oldest element when full. Returns the
        /// element that was evicted, or `null` if nothing was dropped. This is
        /// the "sliding window" mode often wanted for logs / recent-N caches.
        pub fn pushOverwrite(self: *Self, value: T) ?T {
            if (!self.isFull()) {
                // Safe: there is room, so push cannot fail.
                self.push(value) catch unreachable;
                return null;
            }
            const evicted = self.buffer[self.head];
            self.buffer[self.head] = value;
            self.head = (self.head + 1) % self.buffer.len;
            return evicted;
        }

        /// Dequeue from the head, or `null` when empty.
        pub fn pop(self: *Self) ?T {
            if (self.isEmpty()) return null;
            const value = self.buffer[self.head];
            self.head = (self.head + 1) % self.buffer.len;
            self.len -= 1;
            return value;
        }

        /// Look at the head without removing it, or `null` when empty.
        pub fn peek(self: Self) ?T {
            if (self.isEmpty()) return null;
            return self.buffer[self.head];
        }

        /// Drain the buffer in FIFO order into a caller-provided slice and
        /// return the populated prefix. `dest` must be at least `count()` long.
        pub fn copyToSlice(self: *Self, dest: []T) []T {
            std.debug.assert(dest.len >= self.len);
            var i: usize = 0;
            while (self.pop()) |value| : (i += 1) dest[i] = value;
            return dest[0..i];
        }
    };
}

// ----------------------------------------------------------------------------
// Tests use std.testing.allocator so any unfreed buffer fails the run.
// ----------------------------------------------------------------------------

const testing = std.testing;

test "new ring buffer is empty with the requested capacity" {
    var rb = try RingBuffer(u8).init(testing.allocator, 3);
    defer rb.deinit(testing.allocator);

    try testing.expectEqual(@as(usize, 3), rb.capacity());
    try testing.expectEqual(@as(usize, 0), rb.count());
    try testing.expect(rb.isEmpty());
    try testing.expectEqual(@as(?u8, null), rb.pop());
    try testing.expectEqual(@as(?u8, null), rb.peek());
}

test "FIFO ordering: first in, first out" {
    var rb = try RingBuffer(u8).init(testing.allocator, 3);
    defer rb.deinit(testing.allocator);

    try rb.push('a');
    try rb.push('b');
    try rb.push('c');

    try testing.expectEqual(@as(?u8, 'a'), rb.peek());
    try testing.expectEqual(@as(?u8, 'a'), rb.pop());
    try testing.expectEqual(@as(?u8, 'b'), rb.pop());
    try testing.expectEqual(@as(?u8, 'c'), rb.pop());
    try testing.expectEqual(@as(?u8, null), rb.pop());
}

test "push on a full buffer returns BufferFull (error path)" {
    var rb = try RingBuffer(u8).init(testing.allocator, 2);
    defer rb.deinit(testing.allocator);

    try rb.push(1);
    try rb.push(2);
    try testing.expect(rb.isFull());
    try testing.expectError(error.BufferFull, rb.push(3));
}

test "wraparound: head moves past the end correctly" {
    var rb = try RingBuffer(u8).init(testing.allocator, 3);
    defer rb.deinit(testing.allocator);

    try rb.push(1);
    try rb.push(2);
    _ = rb.pop(); // head advances to index 1
    try rb.push(3);
    try rb.push(4); // wraps to index 0
    try testing.expect(rb.isFull());

    try testing.expectEqual(@as(?u8, 2), rb.pop());
    try testing.expectEqual(@as(?u8, 3), rb.pop());
    try testing.expectEqual(@as(?u8, 4), rb.pop());
}

test "pushOverwrite evicts the oldest element when full" {
    var rb = try RingBuffer(u8).init(testing.allocator, 2);
    defer rb.deinit(testing.allocator);

    try testing.expectEqual(@as(?u8, null), rb.pushOverwrite(1));
    try testing.expectEqual(@as(?u8, null), rb.pushOverwrite(2));
    // Now full; the next overwrite evicts the oldest (1).
    try testing.expectEqual(@as(?u8, 1), rb.pushOverwrite(3));
    try testing.expectEqual(@as(?u8, 2), rb.pushOverwrite(4));

    try testing.expectEqual(@as(?u8, 3), rb.pop());
    try testing.expectEqual(@as(?u8, 4), rb.pop());
}

test "copyToSlice drains in FIFO order into a slice" {
    var rb = try RingBuffer(i32).init(testing.allocator, 4);
    defer rb.deinit(testing.allocator);

    try rb.push(5);
    try rb.push(6);
    try rb.push(7);

    var dest: [4]i32 = undefined;
    const drained = rb.copyToSlice(&dest);

    try testing.expectEqualSlices(i32, &.{ 5, 6, 7 }, drained);
    try testing.expect(rb.isEmpty());
}
