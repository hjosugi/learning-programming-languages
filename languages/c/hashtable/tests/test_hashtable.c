/*
 * test_hashtable.c - assert()-based unit tests for the hash table.
 *
 * Plain C, no framework: each test is a function full of assert()s, registered
 * in a small table and run in sequence. A failing assert() aborts with a
 * non-zero exit status, which is exactly what `make test` checks for. Build
 * with `make asan` to run this same suite under AddressSanitizer + UBSan.
 *
 * NOTE: assert() compiles out under -DNDEBUG. The Makefile deliberately does
 * NOT define NDEBUG for tests, so the asserts are live.
 */
#include "hashtable.h"

#include <assert.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

/* ---- individual test cases --------------------------------------------- */

static void test_create_and_empty(void) {
    hashtable *ht = ht_create(0);          /* 0 -> rounded up to min cap */
    assert(ht != NULL);
    assert(ht_size(ht) == 0);
    assert(ht_capacity(ht) >= 8);
    assert(!ht_contains(ht, "anything"));

    long out = 123;
    assert(!ht_get(ht, "anything", &out));
    assert(out == 123);                    /* out untouched on miss */

    ht_free(ht);
}

static void test_set_get_basic(void) {
    hashtable *ht = ht_create(8);
    assert(ht != NULL);

    assert(ht_set(ht, "alpha", 1));
    assert(ht_set(ht, "beta", 2));
    assert(ht_set(ht, "gamma", 3));
    assert(ht_size(ht) == 3);

    long v = 0;
    assert(ht_get(ht, "alpha", &v) && v == 1);
    assert(ht_get(ht, "beta", &v)  && v == 2);
    assert(ht_get(ht, "gamma", &v) && v == 3);
    assert(ht_contains(ht, "alpha"));
    assert(!ht_contains(ht, "delta"));

    ht_free(ht);
}

static void test_overwrite_keeps_size(void) {
    hashtable *ht = ht_create(8);
    assert(ht != NULL);

    assert(ht_set(ht, "k", 10));
    assert(ht_size(ht) == 1);
    assert(ht_set(ht, "k", 20));           /* overwrite, not insert */
    assert(ht_size(ht) == 1);              /* size must NOT grow */

    long v = 0;
    assert(ht_get(ht, "k", &v) && v == 20);

    ht_free(ht);
}

static void test_get_with_null_out(void) {
    hashtable *ht = ht_create(8);
    assert(ht != NULL);
    assert(ht_set(ht, "x", 7));
    assert(ht_get(ht, "x", NULL));         /* presence check, no out write */
    assert(!ht_get(ht, "y", NULL));
    ht_free(ht);
}

static void test_grow_and_rehash(void) {
    /* Start tiny so we definitely cross the load factor and rehash. */
    hashtable *ht = ht_create(8);
    assert(ht != NULL);
    size_t cap0 = ht_capacity(ht);

    enum { N = 500 };
    char key[32];
    for (int i = 0; i < N; ++i) {
        snprintf(key, sizeof(key), "item-%d", i);
        assert(ht_set(ht, key, i));
    }
    assert(ht_size(ht) == (size_t)N);
    assert(ht_capacity(ht) > cap0);        /* it actually grew */

    /* Load factor stayed under 0.75 after the final grow. */
    assert(ht_size(ht) * 4 <= ht_capacity(ht) * 3);

    /* EVERY key survived the rehashes with the right value. */
    for (int i = 0; i < N; ++i) {
        snprintf(key, sizeof(key), "item-%d", i);
        long v = -1;
        assert(ht_get(ht, key, &v));
        assert(v == i);
    }
    ht_free(ht);
}

static void test_remove(void) {
    hashtable *ht = ht_create(8);
    assert(ht != NULL);

    assert(ht_set(ht, "a", 1));
    assert(ht_set(ht, "b", 2));
    assert(ht_set(ht, "c", 3));
    assert(ht_size(ht) == 3);

    assert(ht_remove(ht, "b"));            /* middle of a possible chain */
    assert(ht_size(ht) == 2);
    assert(!ht_contains(ht, "b"));
    assert(ht_contains(ht, "a"));
    assert(ht_contains(ht, "c"));

    assert(!ht_remove(ht, "b"));           /* second remove is a no-op */
    assert(!ht_remove(ht, "never"));       /* absent key */
    assert(ht_size(ht) == 2);

    /* Reinsert a removed key works and is fresh. */
    assert(ht_set(ht, "b", 99));
    long v = 0;
    assert(ht_get(ht, "b", &v) && v == 99);
    assert(ht_size(ht) == 3);

    ht_free(ht);
}

static void test_remove_all_then_reuse(void) {
    hashtable *ht = ht_create(8);
    assert(ht != NULL);

    char key[32];
    for (int i = 0; i < 50; ++i) {
        snprintf(key, sizeof(key), "n%d", i);
        assert(ht_set(ht, key, i * 2));
    }
    assert(ht_size(ht) == 50);

    for (int i = 0; i < 50; ++i) {
        snprintf(key, sizeof(key), "n%d", i);
        assert(ht_remove(ht, key));
    }
    assert(ht_size(ht) == 0);
    assert(!ht_contains(ht, "n0"));

    /* Empty-but-not-fresh table still works. */
    assert(ht_set(ht, "again", 1));
    assert(ht_contains(ht, "again"));
    ht_free(ht);
}

static void test_keys_snapshot(void) {
    hashtable *ht = ht_create(8);
    assert(ht != NULL);

    /* Empty table: ht_keys returns NULL with count 0. */
    size_t n = 99;
    const char **empty = ht_keys(ht, &n);
    assert(empty == NULL && n == 0);

    const char *want[] = {"red", "green", "blue"};
    const size_t want_n = sizeof(want) / sizeof(want[0]);
    for (size_t i = 0; i < want_n; ++i) {
        assert(ht_set(ht, want[i], (long)i));
    }

    const char **keys = ht_keys(ht, &n);
    assert(keys != NULL);
    assert(n == want_n);

    /* Every expected key appears exactly once (order is unspecified). */
    for (size_t w = 0; w < want_n; ++w) {
        int seen = 0;
        for (size_t i = 0; i < n; ++i) {
            if (strcmp(keys[i], want[w]) == 0) {
                seen++;
            }
        }
        assert(seen == 1);
    }
    free(keys);                            /* caller owns the array */
    ht_free(ht);
}

static void test_caller_buffer_is_copied(void) {
    /* Prove the table owns its OWN copy of the key, not the caller's buffer. */
    hashtable *ht = ht_create(8);
    assert(ht != NULL);

    char buf[16];
    strcpy(buf, "mutable");
    assert(ht_set(ht, buf, 1));
    strcpy(buf, "ZZZZZZZ");                /* clobber caller's buffer */

    assert(ht_contains(ht, "mutable"));    /* table copy unaffected */
    assert(!ht_contains(ht, "ZZZZZZZ"));
    ht_free(ht);
}

static void test_empty_string_key(void) {
    hashtable *ht = ht_create(8);
    assert(ht != NULL);
    assert(ht_set(ht, "", 42));            /* "" is a valid key */
    long v = 0;
    assert(ht_get(ht, "", &v) && v == 42);
    assert(ht_size(ht) == 1);
    assert(ht_remove(ht, ""));
    assert(ht_size(ht) == 0);
    ht_free(ht);
}

static void test_null_defensive(void) {
    /* Every entry point must tolerate NULL without crashing. */
    long v = 5;
    assert(!ht_set(NULL, "k", 1));
    assert(!ht_get(NULL, "k", &v));
    assert(v == 5);
    assert(!ht_contains(NULL, "k"));
    assert(!ht_remove(NULL, "k"));
    assert(ht_size(NULL) == 0);
    assert(ht_capacity(NULL) == 0);

    size_t n = 7;
    assert(ht_keys(NULL, &n) == NULL && n == 0);
    ht_free(NULL);                         /* must be a safe no-op */

    /* NULL key on a real table is also rejected. */
    hashtable *ht = ht_create(8);
    assert(ht != NULL);
    assert(!ht_set(ht, NULL, 1));
    assert(!ht_get(ht, NULL, &v));
    assert(!ht_remove(ht, NULL));
    ht_free(ht);
}

/* ---- runner ------------------------------------------------------------ */

typedef struct {
    const char *name;
    void      (*fn)(void);
} test_case;

int main(void) {
    const test_case tests[] = {
        {"create_and_empty",       test_create_and_empty},
        {"set_get_basic",          test_set_get_basic},
        {"overwrite_keeps_size",   test_overwrite_keeps_size},
        {"get_with_null_out",      test_get_with_null_out},
        {"grow_and_rehash",        test_grow_and_rehash},
        {"remove",                 test_remove},
        {"remove_all_then_reuse",  test_remove_all_then_reuse},
        {"keys_snapshot",          test_keys_snapshot},
        {"caller_buffer_is_copied",test_caller_buffer_is_copied},
        {"empty_string_key",       test_empty_string_key},
        {"null_defensive",         test_null_defensive},
    };
    const size_t n = sizeof(tests) / sizeof(tests[0]);

    for (size_t i = 0; i < n; ++i) {
        printf("[ RUN  ] %s\n", tests[i].name);
        tests[i].fn();                     /* aborts on first failed assert */
        printf("[  OK  ] %s\n", tests[i].name);
    }

    printf("\nAll %zu test cases passed.\n", n);
    return EXIT_SUCCESS;
}
