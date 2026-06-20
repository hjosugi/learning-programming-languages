/*
 * hashtable.c - implementation of the separate-chaining hash table.
 *
 * Signature C concepts on display here:
 *   - manual malloc/calloc/realloc/free with one clear owner per allocation;
 *   - pointer-to-pointer traversal for O(1) unlink without a "prev" variable;
 *   - struct allocation and field ownership;
 *   - defensive NULL handling on every entry point;
 *   - a growth policy (power-of-two capacity, load-factor trigger, rehash).
 */
#include "hashtable.h"

#include <stdint.h>
#include <stdlib.h>
#include <string.h>

/* Grow when size/capacity would exceed 0.75 (3/4). */
#define HT_MAX_LOAD_NUM 3u
#define HT_MAX_LOAD_DEN 4u
#define HT_MIN_CAPACITY 8u

/* ----------------------------------------------------------------------------
 * Internal helpers
 * ------------------------------------------------------------------------- */

/* Round up to the next power of two (>= HT_MIN_CAPACITY). */
static size_t next_pow2(size_t n) {
    size_t cap = HT_MIN_CAPACITY;
    while (cap < n) {
        size_t doubled = cap << 1;
        if (doubled < cap) { /* overflow guard */
            return cap;
        }
        cap = doubled;
    }
    return cap;
}

/*
 * FNV-1a, a small well-known string hash. Good enough to demonstrate bucket
 * distribution; not cryptographic. Returns a 64-bit value we mask down.
 */
static uint64_t fnv1a(const char *s) {
    const uint64_t FNV_OFFSET = 1469598103934665603ULL;
    const uint64_t FNV_PRIME  = 1099511628211ULL;
    uint64_t h = FNV_OFFSET;
    for (const unsigned char *p = (const unsigned char *)s; *p; ++p) {
        h ^= (uint64_t)*p;
        h *= FNV_PRIME;
    }
    return h;
}

/* Map a key to a bucket index. capacity is a power of two, so mask = cap-1. */
static size_t bucket_index(const char *key, size_t capacity) {
    return (size_t)(fnv1a(key) & (uint64_t)(capacity - 1));
}

/* strdup is POSIX, not C17; provide our own so -std=c17 -Werror is clean. */
static char *dup_str(const char *s) {
    size_t n = strlen(s) + 1;
    char *copy = malloc(n);
    if (copy != NULL) {
        memcpy(copy, s, n);
    }
    return copy;
}

/*
 * Allocate a fresh bucket array of `capacity` zeroed chain heads.
 * Returns NULL on failure.
 */
static ht_entry **alloc_buckets(size_t capacity) {
    return calloc(capacity, sizeof(ht_entry *));
}

/*
 * Grow the table to `new_capacity` and rehash every entry into the new array.
 * Reuses the existing entry nodes (only the bucket array is reallocated), so
 * no key strings are copied or freed. Returns true on success; on failure the
 * table is left fully intact at its old capacity.
 */
static bool ht_resize(hashtable *ht, size_t new_capacity) {
    ht_entry **new_buckets = alloc_buckets(new_capacity);
    if (new_buckets == NULL) {
        return false;
    }

    /* Move each existing node to its new bucket (prepend; order within a
     * bucket does not matter). */
    for (size_t i = 0; i < ht->capacity; ++i) {
        ht_entry *node = ht->buckets[i];
        while (node != NULL) {
            ht_entry *next = node->next;            /* save before relinking */
            size_t idx = bucket_index(node->key, new_capacity);
            node->next = new_buckets[idx];
            new_buckets[idx] = node;
            node = next;
        }
    }

    free(ht->buckets);          /* free only the old array of pointers */
    ht->buckets = new_buckets;
    ht->capacity = new_capacity;
    return true;
}

/* True if adding one more entry would push us over the load factor. */
static bool over_load(size_t size, size_t capacity) {
    /* (size+1)/capacity > 3/4  <=>  (size+1)*4 > capacity*3 */
    return (size + 1) * HT_MAX_LOAD_DEN > capacity * HT_MAX_LOAD_NUM;
}

/* ----------------------------------------------------------------------------
 * Public API
 * ------------------------------------------------------------------------- */

hashtable *ht_create(size_t initial_capacity) {
    hashtable *ht = malloc(sizeof(*ht));
    if (ht == NULL) {
        return NULL;
    }
    ht->capacity = next_pow2(initial_capacity == 0 ? HT_MIN_CAPACITY
                                                   : initial_capacity);
    ht->size = 0;
    ht->buckets = alloc_buckets(ht->capacity);
    if (ht->buckets == NULL) {
        free(ht);               /* don't leak the table on bucket failure */
        return NULL;
    }
    return ht;
}

void ht_free(hashtable *ht) {
    if (ht == NULL) {
        return;                 /* defensive: free(NULL)-style no-op */
    }
    for (size_t i = 0; i < ht->capacity; ++i) {
        ht_entry *node = ht->buckets[i];
        while (node != NULL) {
            ht_entry *next = node->next;
            free(node->key);    /* free the owned key copy ... */
            free(node);         /* ... then the node itself */
            node = next;
        }
    }
    free(ht->buckets);
    free(ht);
}

bool ht_set(hashtable *ht, const char *key, long value) {
    if (ht == NULL || key == NULL) {
        return false;
    }

    /* Overwrite path: if the key already exists, just replace the value. */
    size_t idx = bucket_index(key, ht->capacity);
    for (ht_entry *node = ht->buckets[idx]; node != NULL; node = node->next) {
        if (strcmp(node->key, key) == 0) {
            node->value = value;
            return true;
        }
    }

    /* Insert path: grow first so we hash into the final array. We do the
     * allocations that can fail BEFORE mutating the table, so a failure
     * leaves the table unchanged. */
    if (over_load(ht->size, ht->capacity)) {
        size_t bigger = ht->capacity << 1;
        if (bigger > ht->capacity && !ht_resize(ht, bigger)) {
            return false;       /* OOM during grow: leave table intact */
        }
        idx = bucket_index(key, ht->capacity); /* recompute after resize */
    }

    char *key_copy = dup_str(key);
    if (key_copy == NULL) {
        return false;
    }
    ht_entry *node = malloc(sizeof(*node));
    if (node == NULL) {
        free(key_copy);         /* don't leak the copy if the node fails */
        return false;
    }
    node->key = key_copy;       /* node now owns the copy */
    node->value = value;
    node->next = ht->buckets[idx];
    ht->buckets[idx] = node;    /* prepend: O(1) insert */
    ht->size++;
    return true;
}

bool ht_get(const hashtable *ht, const char *key, long *out) {
    if (ht == NULL || key == NULL) {
        return false;
    }
    size_t idx = bucket_index(key, ht->capacity);
    for (ht_entry *node = ht->buckets[idx]; node != NULL; node = node->next) {
        if (strcmp(node->key, key) == 0) {
            if (out != NULL) {
                *out = node->value;
            }
            return true;
        }
    }
    return false;
}

bool ht_contains(const hashtable *ht, const char *key) {
    return ht_get(ht, key, NULL);
}

bool ht_remove(hashtable *ht, const char *key) {
    if (ht == NULL || key == NULL) {
        return false;
    }
    size_t idx = bucket_index(key, ht->capacity);

    /* Pointer-to-pointer walk: `link` points at the pointer that points at the
     * current node, so we can unlink without tracking a separate "prev". This
     * is one of the most idiomatic C list patterns. */
    for (ht_entry **link = &ht->buckets[idx]; *link != NULL;
         link = &(*link)->next) {
        ht_entry *node = *link;
        if (strcmp(node->key, key) == 0) {
            *link = node->next; /* splice the node out of the chain */
            free(node->key);    /* free what the node owns ... */
            free(node);         /* ... then the node */
            ht->size--;
            return true;
        }
    }
    return false;
}

size_t ht_size(const hashtable *ht) {
    return ht == NULL ? 0 : ht->size;
}

size_t ht_capacity(const hashtable *ht) {
    return ht == NULL ? 0 : ht->capacity;
}

const char **ht_keys(const hashtable *ht, size_t *out_count) {
    if (ht == NULL) {
        if (out_count != NULL) {
            *out_count = 0;
        }
        return NULL;
    }
    if (ht->size == 0) {
        if (out_count != NULL) {
            *out_count = 0;
        }
        return NULL;            /* nothing to return; caller frees nothing */
    }

    const char **keys = malloc(ht->size * sizeof(*keys));
    if (keys == NULL) {
        if (out_count != NULL) {
            *out_count = 0;
        }
        return NULL;
    }

    size_t n = 0;
    for (size_t i = 0; i < ht->capacity; ++i) {
        for (ht_entry *node = ht->buckets[i]; node != NULL; node = node->next) {
            keys[n++] = node->key; /* borrowed pointer into the table */
        }
    }
    if (out_count != NULL) {
        *out_count = n;
    }
    return keys;                 /* caller owns the array, not the strings */
}
