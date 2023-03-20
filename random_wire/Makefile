all: avoid.png

avoid: avoid.c

avoid.png: avoid avoid.gnuplot
	./avoid > avoid.txt
	gnuplot avoid.gnuplot

avoid.png: avoid avoid.gnuplot
	./avoid > avoid.txt
	gnuplot avoid.gnuplot

clean:
	rm -f avoid avoid.txt avoid.png
