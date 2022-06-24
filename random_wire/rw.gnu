set xtics 5
unset ytics
set grid
set xlabel 'Wire Length (feet)'
set title 'Random Wire Lengths to Avoid'
set term png size 1250,150
set output 'f.png'
plot [:][:1] 'f' with filledcurves notitle
