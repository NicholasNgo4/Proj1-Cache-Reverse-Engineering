CC = gcc

CFLAGS = -O2 -Wall -Wextra -std=c11

TARGET = cache_bench

COMMON_DIR = main_code/common

SOURCES = \
	$(COMMON_DIR)/benchmark.c \
	$(COMMON_DIR)/pointer_chase.c \
	$(COMMON_DIR)/random.c

OBJECTS = $(SOURCES:.c=.o)

all: $(TARGET)

$(TARGET): $(OBJECTS)
	$(CC) $(CFLAGS) -o $@ $^

%.o: %.c
	$(CC) $(CFLAGS) -c $< -o $@

clean:
	rm -f $(TARGET) $(OBJECTS)

.PHONY: all clean