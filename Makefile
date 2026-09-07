CC = gcc

CFLAGS = -O0 -Wall -Wextra -std=c11
LDLIBS = -lm

TARGET = cache_bench

COMMON_DIR = main_code/common

SOURCES = \
	$(COMMON_DIR)/main.c \
	$(COMMON_DIR)/benchmark.c \
	$(COMMON_DIR)/pointer_chase.c \
	$(COMMON_DIR)/random.c \
	$(COMMON_DIR)/capacity.c

OBJECTS = $(SOURCES:.c=.o)

all: $(TARGET)

$(TARGET): $(OBJECTS)
	$(CC) $(CFLAGS) -o $@ $^ $(LDLIBS)

%.o: %.c
	$(CC) $(CFLAGS) -c $< -o $@

clean:
	rm -f $(TARGET) $(OBJECTS)

.PHONY: all clean