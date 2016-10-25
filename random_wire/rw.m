function rw(varargin)
% RW(bands) calculates half-wavelengths in feet of each ham band
% passed in vector bands_m.
%
% EXAMPLES
%   rw([40 20 15 10])
%   rw([80 30 40])
%   rw([15])
%   rw([40 20 15 10], 'cw')
%
% INPUT
%   bands: vector of integers representing a ham band.  For instance,
%          [40 20 15 10] represents the USA amateur 40m, 20m, 15, and 10m
%          ham bands.  If a second argument is provided and is 'cw', then
%          USA cw sub-bands will be graphed.
%
% OUTPUT
%   A graph whose red bands indicate half-wavelengths for the ham bands
%   chosen.  These are the highest impedance lengths for end-fed wires.
%   For typical transceiver antenna tuners, these are lengths to avoid.
%
% Author
%   Mike Markowski AB3AP
%
% Date
%   2013 Feb  5 Original
%   2013 Feb  7 Added provision for 'cw' in varargin.

    bands_m = varargin{1};
    if nargin == 2 && strcmp(varargin{2}, 'cw')
        useCw = 1;
    else
        useCw = 0;
    end

    % Convert ham band names to min/max band edge frequency pairs.
    freqs_kHz = [];
    bands_m = sort(bands_m, 'descend');
    for i = 1:size(bands_m, 2)
        if useCw
            freqs_kHz = [freqs_kHz ; mapBandCw(bands_m(i))];
        else
            freqs_kHz = [freqs_kHz ; mapBand(bands_m(i))];
        end
    end
    lowest_MHz = freqs_kHz(1) * 1e-3;

    % Prepare plot.
    clf
    hold on
    grid on
    figHandle = figure(1);
    screensize = get( 0, 'ScreenSize' );
    scrWidth = screensize(3);
    scrHeight = screensize(4);
    set(figHandle, 'Position', ...
        [scrWidth/2 - 500, scrHeight/2, 150 * size(bands_m, 2), 100]);
    if useCw
        bandStr = ' USA CW Sub-bands';
    else
        bandStr = ' USA Bands';
    end
    title(['End-fed Antenna High Impedance Lengths for ', ...
        mat2str(bands_m), bandStr]);
    xlabel('Lengths to Avoid in Red (ft)');

    % Plot length of zero feet through quarter wave, since antenna
    % must (should) be at least 1/4 wavelength long.
    fullWave_ft = 2 * 468 / lowest_MHz; % Max wavelength in band.
    qtrWave_ft = fullWave_ft / 4;    
    qtrX = [0 0 qtrWave_ft qtrWave_ft];
    qtrY = [0 1 1          0];
    plotProps = area(qtrX, qtrY);
    set(plotProps, 'FaceColor', [1 0 0], 'EdgeColor', [1, 0, 0])
    
    % Draw a rectangle for difficult (high impedance) end fed wire lengths.
    for i = 1:size(freqs_kHz, 1)
        badLengths(freqs_kHz(i, 1), freqs_kHz(i, 2), fullWave_ft)
    end
    set(gca(), 'YTickLabel', '')
    
    % Adjust limits of x axis to multiples of 10 feet.
    shortestQtrWave = 234 / (freqs_kHz(1) * 1e-3);
    shortestQtrWave = 10 * floor(shortestQtrWave / 10);
    xlim([shortestQtrWave, fullWave_ft]);
    % Pick an even increment along x axis.
    inc = (fullWave_ft - shortestQtrWave) / size(bands_m, 2) / 1.5;
    inc = 10 * floor(inc / 10);
    % Matlab default (2012b) uses too few tick marks, so add more.
    set(gca(), 'Xtick', shortestQtrWave:inc:fullWave_ft);
    hold off
end

function minMax = mapBand(band)
% Convert a ham band name to its USA min and max frequencies in kHz.
    switch band
        case 160
            minMax = [1800 2000];
        case 80
            minMax = [3500 4000];
        case 60
            minMax = [5330.5 5405];
        case 40
            minMax = [7000 7300];
        case 30
            minMax = [10100 10150];
        case 20
            minMax = [14000 14350];
        case 17
            minMax = [18068 18168];
        case 15
            minMax = [21000 21450];
        case 12
            minMax = [24890 24990];
        case 10
            minMax = [28000 29700];
        case 6
            minMax = [50000 54000];
        otherwise
            disp('Unexpected amateur band: ', band, ' m')
            minMax = [];
    end 
end

function minMax = mapBandCw(band)
% Convert a ham band name to its USA min and max frequencies in kHz for
% CW sub-bands.
    switch band
        case 160
            minMax = [1800 2000];
        case 80
            minMax = [3500 3600];
        case 60
            minMax = [5330.5 5405];
        case 40
            minMax = [7000 7125];
        case 30
            minMax = [10100 10150];
        case 20
            minMax = [14000 14150];
        case 17
            minMax = [18068 18110];
        case 15
            minMax = [21000 21200];
        case 12
            minMax = [24890 24930];
        case 10
            minMax = [28000 28300];
        case 6
            minMax = [50000 54000];
        otherwise
            disp('Unexpected amateur band: ', band, ' m')
            minMax = [];
    end 
end

function badLengths(min_kHz, max_kHz, fullWave_ft)
% Plot a solid rectangle covering the frequency range half-wavelengths in
% ft.

    n = 1;
    while 1
        % For each min/max frequency delimiting a range, draw a rectangle
        % indicating bad, or very high impedance, end-fed wire lengths.
        lambda0_ft = n * 468 / (max_kHz * 1e-3);
        lambda1_ft = n * 468 / (min_kHz * 1e-3);
        badX = [lambda0_ft lambda0_ft lambda1_ft lambda1_ft];
        badY = [0          1          1          0];
        plotProps = area(badX, badY);
        set(plotProps, 'FaceColor', [1 0 0], 'EdgeColor', [1, 0, 0])
        n = n + 1;
        if lambda1_ft > fullWave_ft || n > 51
            break
        end
    end
end
