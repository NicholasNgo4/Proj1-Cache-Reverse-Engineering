CC = gcc

CFLAGS = -O0 -g -std=c11 -Wall -Wextra -fno-omit-frame-pointer
LDLIBS = -lm

TARGET = cache_bench

COMMON_DIR = main_code/common

SOURCES = \
	$(COMMON_DIR)/main.c \
	$(COMMON_DIR)/benchmark.c \
	$(COMMON_DIR)/pointer_chase.c \
	$(COMMON_DIR)/random.c \
	$(COMMON_DIR)/capacity.c \
	$(COMMON_DIR)/line_size.c \
	$(COMMON_DIR)/associativity.c \
	$(COMMON_DIR)/latency.c

OBJECTS = $(SOURCES:.c=.o)

all: $(TARGET)

$(TARGET): $(OBJECTS)
	$(CC) $(CFLAGS) -o $@ $^ $(LDLIBS)

%.o: %.c
	$(CC) $(CFLAGS) -c $< -o $@

clean:
	rm -f $(TARGET) $(OBJECTS)

.PHONY: all clean