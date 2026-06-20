# Makefile for the learning-c hash table hands-on.
#
# Targets:
#   all    build the demo into bin/demo            (default)
#   run    build + run the demo
#   test   build + run the assert-based test suite (exit non-zero on failure)
#   asan   build the tests with AddressSanitizer + UBSan and run them
#   clean  remove all build artifacts
#
# Override the compiler:  make CC=clang
# gcc and clang are both on PATH on this machine; gcc is the default.

CC      ?= gcc
CSTD    := -std=c17
WARN    := -Wall -Wextra -Werror
CFLAGS  := $(CSTD) $(WARN) -O2 -g -Isrc
ASAN    := -fsanitize=address,undefined -fno-omit-frame-pointer

BIN     := bin
SRC     := src/hashtable.c
DEMO    := src/main.c
TEST    := tests/test_hashtable.c

DEMO_BIN := $(BIN)/demo
TEST_BIN := $(BIN)/test_hashtable
ASAN_BIN := $(BIN)/test_hashtable_asan

.PHONY: all run test asan clean

all: $(DEMO_BIN)

$(BIN):
	mkdir -p $(BIN)

# --- demo ----------------------------------------------------------------
$(DEMO_BIN): $(DEMO) $(SRC) src/hashtable.h | $(BIN)
	$(CC) $(CFLAGS) -o $@ $(DEMO) $(SRC)

run: $(DEMO_BIN)
	./$(DEMO_BIN)

# --- tests ---------------------------------------------------------------
$(TEST_BIN): $(TEST) $(SRC) src/hashtable.h | $(BIN)
	$(CC) $(CFLAGS) -o $@ $(TEST) $(SRC)

test: $(TEST_BIN)
	./$(TEST_BIN)

# --- tests under AddressSanitizer + UBSan --------------------------------
# Rebuilt every time (.PHONY-ish via no prereq tracking on the binary) so the
# sanitizer flags are always applied. UBSAN_OPTIONS makes UB a hard failure.
asan: $(TEST) $(SRC) src/hashtable.h | $(BIN)
	$(CC) $(CSTD) $(WARN) -g -O1 $(ASAN) -Isrc -o $(ASAN_BIN) $(TEST) $(SRC)
	ASAN_OPTIONS=detect_leaks=1 UBSAN_OPTIONS=halt_on_error=1:print_stacktrace=1 ./$(ASAN_BIN)

clean:
	rm -rf $(BIN)
