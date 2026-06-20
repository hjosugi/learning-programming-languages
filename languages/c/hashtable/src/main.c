/*
 * main.c - a small, narrated demo of the hash table.
 *
 * Run it (see README "## Run") to watch insert / overwrite / get / remove and,
 * most importantly, an automatic grow+rehash where you can SEE the capacity
 * double while every key/value survives. Build with `asan` to prove no leaks.
 */
#include "hashtable.h"

#include <stdio.h>
#include <stdlib.h>

/* Word-count a fixed input so the demo is deterministic and offline. */
static const char *const WORDS[] = {
    "the", "quick", "brown", "fox", "jumps", "over", "the", "lazy",
    "dog", "the", "fox", "is", "quick", "and", "the", "dog", "is",
    "lazy", "but", "the", "quick", "fox", "wins",
};
static const size_t WORD_COUNT = sizeof(WORDS) / sizeof(WORDS[0]);

int main(void) {
    printf("== learning-c: separate-chaining hash table demo ==\n\n");

    hashtable *ht = ht_create(8);
    if (ht == NULL) {
        fprintf(stderr, "out of memory creating table\n");
        return EXIT_FAILURE;
    }
    printf("created table: capacity=%zu size=%zu\n\n",
           ht_capacity(ht), ht_size(ht));

    /* 1. Word frequency count: classic hash-table use. ----------------- */
    printf("counting %zu words ...\n", WORD_COUNT);
    for (size_t i = 0; i < WORD_COUNT; ++i) {
        long count = 0;
        ht_get(ht, WORDS[i], &count);      /* 0 if absent */
        if (!ht_set(ht, WORDS[i], count + 1)) {
            fprintf(stderr, "ht_set failed (out of memory)\n");
            ht_free(ht);
            return EXIT_FAILURE;
        }
    }
    printf("distinct words=%zu  capacity now=%zu\n\n",
           ht_size(ht), ht_capacity(ht));

    /* 2. Look a few up. ------------------------------------------------ */
    const char *probe[] = {"the", "fox", "dog", "missing"};
    for (size_t i = 0; i < sizeof(probe) / sizeof(probe[0]); ++i) {
        long v = 0;
        if (ht_get(ht, probe[i], &v)) {
            printf("  %-8s -> %ld\n", probe[i], v);
        } else {
            printf("  %-8s -> (absent)\n", probe[i]);
        }
    }
    printf("\n");

    /* 3. Force a visible grow: insert many distinct keys. -------------- */
    size_t cap_before = ht_capacity(ht);
    printf("inserting key_0..key_99 to trigger grows (cap before=%zu) ...\n",
           cap_before);
    for (int i = 0; i < 100; ++i) {
        char key[32];
        snprintf(key, sizeof(key), "key_%d", i);
        if (!ht_set(ht, key, i)) {         /* key buffer is reused/copied */
            fprintf(stderr, "ht_set failed\n");
            ht_free(ht);
            return EXIT_FAILURE;
        }
    }
    printf("after inserts: size=%zu capacity=%zu (load factor kept under 0.75)\n\n",
           ht_size(ht), ht_capacity(ht));

    /* Survival check: a value inserted before the grow is still correct. */
    long the_count = -1;
    ht_get(ht, "the", &the_count);
    printf("\"the\" survived all rehashes with count=%ld\n\n", the_count);

    /* 4. Remove, and prove it is gone. -------------------------------- */
    printf("removing \"key_42\": %s\n",
           ht_remove(ht, "key_42") ? "removed" : "not found");
    printf("contains \"key_42\" now? %s\n\n",
           ht_contains(ht, "key_42") ? "yes" : "no");

    /* 5. Snapshot keys (caller owns the array, not the strings). ------- */
    size_t k = 0;
    const char **keys = ht_keys(ht, &k);
    printf("ht_keys returned %zu keys; first few: ", k);
    for (size_t i = 0; i < k && i < 5; ++i) {
        printf("%s ", keys[i]);
    }
    printf("...\n");
    free(keys);                            /* free the array; NOT the strings */

    ht_free(ht);                           /* releases everything else */
    printf("\nfreed table. run `make asan` to verify zero leaks.\n");
    return EXIT_SUCCESS;
}
