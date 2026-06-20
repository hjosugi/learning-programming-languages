/*
 * hashtable.h - Separate-chaining hash table (string keys, long values).
 *
 * Public interface only. The struct layouts live in hashtable.c so callers
 * cannot poke at internals; this is the classic C "opaque-ish" header/impl
 * split. (We expose the struct shape here for the demo's introspection, but
 * everything you should *touch* goes through the functions below.)
 *
 * OWNERSHIP CONTRACT (read this; it is the whole point of the exercise):
 *
 *   - The table OWNS a private, heap-allocated copy of every key string you
 *     insert. You keep ownership of the `const char *` you pass in; we strdup
 *     it. You may free or reuse your buffer immediately after the call.
 *   - The table does NOT own the `long` values; they are stored by value.
 *   - ht_get / ht_keys return BORROWED pointers into the table. They are valid
 *     only until the next mutating call (ht_set / ht_remove / ht_free) that may
 *     rehash or free the node. Do not free them.
 *   - The caller OWNS the array returned by ht_keys and must free() it (but NOT
 *     the strings it points at - those stay owned by the table).
 *   - ht_free releases everything the table owns; using the table afterward is
 *     undefined behaviour.
 *
 * Every function is defensive about NULL: passing a NULL table is a no-op /
 * sentinel return, never a crash.
 */
#ifndef LEARNING_C_HASHTABLE_H
#define LEARNING_C_HASHTABLE_H

#include <stdbool.h>
#include <stddef.h>

/* One key/value pair, living in a singly-linked bucket chain. */
typedef struct ht_entry {
    char            *key;   /* owned: heap copy of the caller's key */
    long             value; /* stored by value */
    struct ht_entry *next;  /* next entry in the same bucket */
} ht_entry;

/* The table itself. `buckets` is an array of `capacity` chain heads. */
typedef struct {
    ht_entry **buckets;  /* owned: array of `capacity` pointers (may be NULL) */
    size_t     capacity; /* number of buckets; always a power of two, or 0 */
    size_t     size;     /* number of live key/value pairs */
} hashtable;

/*
 * Create an empty table.
 * `initial_capacity` is a hint; it is rounded up to a power of two (min 8).
 * Returns a heap-allocated table the caller OWNS (free with ht_free), or NULL
 * on allocation failure.
 */
hashtable *ht_create(size_t initial_capacity);

/* Release the table and everything it owns. Safe to call with NULL. */
void ht_free(hashtable *ht);

/*
 * Insert or overwrite `key` -> `value`.
 * On first insert the key is strdup'd (table takes a copy). On overwrite the
 * existing value is replaced and no allocation happens.
 * May trigger a grow+rehash when the load factor is exceeded.
 * Returns true on success, false on allocation failure or NULL args. On
 * failure the table is left unchanged (strong-ish guarantee for this op).
 */
bool ht_set(hashtable *ht, const char *key, long value);

/*
 * Look up `key`. If found, returns true and (when `out` != NULL) writes the
 * value to *out. Returns false if absent or on NULL args. Does not allocate.
 */
bool ht_get(const hashtable *ht, const char *key, long *out);

/* True iff `key` is present. Convenience wrapper over ht_get. */
bool ht_contains(const hashtable *ht, const char *key);

/*
 * Remove `key` if present, freeing the table's owned copy of it.
 * Returns true if something was removed, false otherwise (incl. NULL args).
 */
bool ht_remove(hashtable *ht, const char *key);

/* Number of live entries. NULL table -> 0. */
size_t ht_size(const hashtable *ht);

/* Number of buckets. NULL table -> 0. */
size_t ht_capacity(const hashtable *ht);

/*
 * Snapshot of all live keys.
 * Returns a freshly malloc'd array of `ht_size(ht)` BORROWED `const char *`
 * (pointing into the table). The CALLER owns and must free() the array; the
 * strings stay owned by the table. When `out_count` != NULL it receives the
 * length. Returns NULL on allocation failure or NULL table. For an empty table
 * returns a valid pointer (malloc(0)-style) with *out_count == 0... we return
 * NULL with *out_count 0 to keep it simple - see impl.
 */
const char **ht_keys(const hashtable *ht, size_t *out_count);

#endif /* LEARNING_C_HASHTABLE_H */
