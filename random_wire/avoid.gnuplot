set xtics 5
unset ytics
set grid
set xlabel 'Wire Length (feet)'
set title 'Random Wire Lengths to Avoid'
set term png size 4000,150
set output 'avoid.png'
plot [:][:1] 'avoid.txt' with filledcurves notitle
