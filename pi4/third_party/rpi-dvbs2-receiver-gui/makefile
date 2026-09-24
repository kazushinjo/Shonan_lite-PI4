CC = gcc
CFLAGS = $(shell pkg-config --cflags gtk4)
LIBS = $(shell pkg-config --libs gtk4)

app: main4.c
	$(CC) main4.c -o app $(CFLAGS) $(LIBS)

clean:
	rm -f app
