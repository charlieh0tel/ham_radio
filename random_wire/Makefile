all: avoid.png

avoid: avoid.c

avoid.png: avoid avoid.gnuplot
	./avoid > avoid.txt
	gnuplot avoid.gnuplot

clean:
	rm -f avoid.txt avoid.pn avoid
