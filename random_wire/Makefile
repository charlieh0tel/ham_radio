all: avoid.png

rw: rw.c

avoid.png: rw rw.gnuplot
	./rw > f
	gnuplot rw.gnuplot
	mv f.png avoid.png

clean:
	rm -f rw f f.png avoid.png
