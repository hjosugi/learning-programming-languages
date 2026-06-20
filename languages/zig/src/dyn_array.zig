//! DynArray: a comptime-generic, growable array (a teaching-sized `ArrayList`).
//!
//! This file is the centerpiece of the hands-on. It deliberately re-implements
//! the core of `std.ArrayList` so the SIGNATURE Zig features are on display in
//! one place:
//!
//!   * comptime generics  -> `DynArray(comptime T: type)` returns a *type*.
//!   * explicit allocators -> every operation that may allocate takes an
//!                            `std.mem.Allocator`; the struct stores no allocator
//!                            so the same array can be moved between allocators.
//!   * error unions        -> growth returns `Allocator.Error!void`; `pop`/`get`
//!                            return optionals; out-of-range access returns a
//!                            named error from `IndexError`.
//!   * optionals           -> `pop`, `getOrNull`, and `last` return `?T`.
//!   * slices              -> `items()` exposes the live data as a `[]T` slice.
//!
//! Idiomatic notes:
//!   * The struct owns a buffer (`buffer: []T`) and a logical length (`len`).
//!     `buffer.len` is the capacity; `len <= buffer.len` always holds.
//!   * `.empty` is the canonical zero value, so callers write
//!     `var a: DynArray(u8) = .empty;` and never need a separate `init`.

const std = @import("std");
const Allocator = std.mem.Allocator;
const assert = std.debug.assert;

/// Errors specific to bounds-checked access. Kept as its own small error set so
/// callers can `catch` exactly this failure and nothing else.
pub const IndexError = error{IndexOutOfBounds};

/// `DynArray(T)` is a function evaluated at *compile time* that returns a new
/// struct type specialized for `T`. This is Zig's whole generics story: types
/// are values you can compute. Each distinct `T` produces a distinct, fully
/// monomorphized type with no runtime type tags.
pub fn DynArray(comptime T: type) type {
    return struct {
        const Self = @This();

        /// Backing storage. `buffer.len` is the capacity.
        buffer: []T,
        /// Number of initialized elements. Invariant: `len <= buffer.len`.
        len: usize,

        /// Canonical empty value. No allocation happens until the first append,
        /// so constructing an empty array can never fail.
        pub const empty: Self = .{ .buffer = &.{}, .len = 0 };

        /// Release the backing buffer. Safe to call on `.empty` (freeing a
        /// zero-length slice is a no-op). After `deinit` the array is `.empty`.
        pub fn deinit(self: *Self, gpa: Allocator) void {
            gpa.free(self.buffer);
            self.* = .empty;
        }

        /// Current number of elements.
        pub fn count(self: Self) usize {
            return self.len;
        }

        /// Current capacity (elements that fit before the next reallocation).
        pub fn capacity(self: Self) usize {
            return self.buffer.len;
        }

        /// The live elements as a mutable slice. Borrowed view: it is
        /// invalidated by any operation that may reallocate (append/grow).
        pub fn items(self: Self) []T {
            return self.buffer[0..self.len];
        }

        /// Ensure capacity for at least `wanted` total elements. Uses an
        /// amortized growth factor so a sequence of appends is O(n) overall.
        pub fn ensureCapacity(self: *Self, gpa: Allocator, wanted: usize) Allocator.Error!void {
            if (self.buffer.len >= wanted) return;

            // Classic geometric growth: grow by ~1.5x, but never by less than
            // what the caller asked for.
            var new_cap = self.buffer.len;
            if (new_cap == 0) new_cap = 4;
            while (new_cap < wanted) new_cap += new_cap / 2 + 1;

            // `realloc` on a zero-length slice behaves like `alloc`.
            self.buffer = try gpa.realloc(self.buffer, new_cap);
        }

        /// Append one element, growing if needed. Returns an error union: the
        /// only failure mode is allocation failure, surfaced as
        /// `error.OutOfMemory`.
        pub fn append(self: *Self, gpa: Allocator, value: T) Allocator.Error!void {
            try self.ensureCapacity(gpa, self.len + 1);
            self.buffer[self.len] = value;
            self.len += 1;
        }

        /// Append every element of a slice. Demonstrates taking a `[]const T`
        /// slice parameter and a single up-front capacity reservation.
        pub fn appendSlice(self: *Self, gpa: Allocator, values: []const T) Allocator.Error!void {
            try self.ensureCapacity(gpa, self.len + values.len);
            // `@memcpy` requires equal lengths; the destination is sized to match.
            @memcpy(self.buffer[self.len .. self.len + values.len], values);
            self.len += values.len;
        }

        /// Remove and return the last element, or `null` when empty. The
        /// optional return type forces the caller to handle emptiness — there is
        /// no sentinel value to forget to check.
        pub fn pop(self: *Self) ?T {
            if (self.len == 0) return null;
            self.len -= 1;
            return self.buffer[self.len];
        }

        /// Peek at the last element without removing it, or `null` when empty.
        pub fn last(self: Self) ?T {
            if (self.len == 0) return null;
            return self.buffer[self.len - 1];
        }

        /// Bounds-checked read that reports failure through the error set.
        /// Use this when an out-of-range index is a real error condition.
        pub fn get(self: Self, index: usize) IndexError!T {
            if (index >= self.len) return error.IndexOutOfBounds;
            return self.buffer[index];
        }

        /// Bounds-checked read that reports an out-of-range index as `null`.
        /// Use this when "missing" is an ordinary, expected outcome.
        pub fn getOrNull(self: Self, index: usize) ?T {
            if (index >= self.len) return null;
            return self.buffer[index];
        }

        /// Bounds-checked write through the error set.
        pub fn set(self: *Self, index: usize, value: T) IndexError!void {
            if (index >= self.len) return error.IndexOutOfBounds;
            self.buffer[index] = value;
        }

        /// Drop all elements but keep the allocated capacity for reuse.
        pub fn clearRetainingCapacity(self: *Self) void {
            self.len = 0;
        }

        /// Hand ownership of a right-sized buffer to the caller and reset to
        /// `.empty`. The returned slice must be freed by the caller with the
        /// same allocator. This is the idiomatic "build then ship" pattern.
        pub fn toOwnedSlice(self: *Self, gpa: Allocator) Allocator.Error![]T {
            const result = try gpa.realloc(self.buffer, self.len);
            self.* = .empty;
            return result;
        }
    };
}

// ----------------------------------------------------------------------------
// Tests. `std.testing.allocator` is a leak-detecting allocator: any allocation
// not freed by the end of the test fails the test. That is what makes the
// "explicit allocator" discipline checkable rather than aspirational.
// ----------------------------------------------------------------------------

const testing = std.testing;

test "empty array has zero length and no capacity" {
    var a: DynArray(u8) = .empty;
    defer a.deinit(testing.allocator);

    try testing.expectEqual(@as(usize, 0), a.count());
    try testing.expectEqual(@as(usize, 0), a.capacity());
    try testing.expectEqual(@as(?u8, null), a.last());
    try testing.expectEqual(@as(?u8, null), a.pop());
}

test "append grows length and preserves order" {
    var a: DynArray(i32) = .empty;
    defer a.deinit(testing.allocator);

    for ([_]i32{ 10, 20, 30 }) |v| try a.append(testing.allocator, v);

    try testing.expectEqual(@as(usize, 3), a.count());
    try testing.expectEqualSlices(i32, &.{ 10, 20, 30 }, a.items());
    try testing.expectEqual(@as(?i32, 30), a.last());
}

test "appendSlice copies a slice in one reservation" {
    var a: DynArray(u8) = .empty;
    defer a.deinit(testing.allocator);

    try a.appendSlice(testing.allocator, "hello");
    try a.append(testing.allocator, '!');

    try testing.expectEqualStrings("hello!", a.items());
}

test "pop returns optional and shrinks length" {
    var a: DynArray(u8) = .empty;
    defer a.deinit(testing.allocator);

    try a.appendSlice(testing.allocator, "ab");
    try testing.expectEqual(@as(?u8, 'b'), a.pop());
    try testing.expectEqual(@as(?u8, 'a'), a.pop());
    try testing.expectEqual(@as(?u8, null), a.pop());
    try testing.expectEqual(@as(usize, 0), a.count());
}

test "get reports out-of-bounds via the error set (error path)" {
    var a: DynArray(u8) = .empty;
    defer a.deinit(testing.allocator);

    try a.append(testing.allocator, 'x');
    try testing.expectEqual(@as(u8, 'x'), try a.get(0));

    // The explicit error path: expectError asserts a *specific* error.
    try testing.expectError(error.IndexOutOfBounds, a.get(1));
    try testing.expectError(error.IndexOutOfBounds, a.set(5, 'z'));
}

test "getOrNull treats missing as null instead of an error" {
    var a: DynArray(u8) = .empty;
    defer a.deinit(testing.allocator);

    try a.append(testing.allocator, 'q');
    try testing.expectEqual(@as(?u8, 'q'), a.getOrNull(0));
    try testing.expectEqual(@as(?u8, null), a.getOrNull(99));
}

test "clearRetainingCapacity keeps the buffer for reuse" {
    var a: DynArray(u8) = .empty;
    defer a.deinit(testing.allocator);

    try a.appendSlice(testing.allocator, "abcd");
    const cap_before = a.capacity();
    a.clearRetainingCapacity();

    try testing.expectEqual(@as(usize, 0), a.count());
    try testing.expectEqual(cap_before, a.capacity());
}

test "toOwnedSlice transfers a right-sized buffer (leak-safe path)" {
    var a: DynArray(u8) = .empty;
    // No deinit: ownership of the buffer leaves the array via toOwnedSlice.

    try a.appendSlice(testing.allocator, "owned");
    const slice = try a.toOwnedSlice(testing.allocator);
    defer testing.allocator.free(slice); // caller now owns it

    try testing.expectEqualStrings("owned", slice);
    try testing.expectEqual(@as(usize, 0), a.count());
}

test "works for an arbitrary struct element type (comptime generic)" {
    const Point = struct { x: i32, y: i32 };
    var a: DynArray(Point) = .empty;
    defer a.deinit(testing.allocator);

    try a.append(testing.allocator, .{ .x = 1, .y = 2 });
    try a.append(testing.allocator, .{ .x = 3, .y = 4 });

    try testing.expectEqual(@as(i32, 3), (try a.get(1)).x);
    try testing.expectEqual(@as(usize, 2), a.count());
}
