
PATH_SOURCE = '~/Documents/MATLAB/SILA-AD-Biomarker/';
PATH_INPUT = '~/Desktop/atstaging/sila/input';
PATH_OUTPUT = '~/Desktop/atstaging/sila/output';
COLUMNS = ["PTCMedialTemporalWScore", "PTCOccipitalWScore", "PACFrontalWScore", "PACParietalWScore", "SummarySUVRAmyloid", "SummarySUVRTau"];
CUTOFFS = [2.5, 2.5, 2.5, 2.5, 1.22, 1.35];

%%%%%%%

addpath(PATH_SOURCE);
addpath(fullfile(PATH_SOURCE, "demo"));

infiles = dir(fullfile(PATH_INPUT, '*.csv'));

for i = 1:length(infiles)
    % Load data
    fullpath = fullfile(infiles(i).folder, infiles(i).name);
    df = readtable(fullpath);
    [~, base, ext] = fileparts(fullpath);

    % add a unique numeric subject id
    [uniqueSubs, ~, SubIDs] = unique(df.Subject);
    df.SubjID = SubIDs;

    % create output table
    output = table;
    output.Subject = df.Subject;
    output.Session = df.Session;
    output.SubjID = df.SubjID;
    
    disp(" ");
    fprintf('Running SILA for file: %s\n', fullpath);
    
    % main loop
    for j = 1:length(COLUMNS)
        column = COLUMNS(j);
        cutoff = CUTOFFS(j);
        fprintf('  > %s (%s)\n', column, cutoff);

        % run SILA
        [tsila,tdrs] = SILA(df.Age, df.(column), df.SubjID, 0.25, cutoff, 200);
        test = SILA_estimate(tsila, df.Age,df.(column),df.SubjID, "align_event", "first");
        
        newcol = sprintf('EstAgeOnset%s', column);
        output.(newcol) = test.estaget0;

        % save the SILA curve
        path = fullfile(PATH_OUTPUT, sprintf('%s_%s_curve.csv', base, column));
        writetable(tsila, path);

        % figure('Units','centimeters','Position',[2,2,12,8])
        % spaghetti_plot(test.estdtt0,test.val,test.subid)
        % plot(tsila.adtime,tsila.val,'-k'),hold on
        % title('Data Aligned by Estimated Time to Threshold')
        % xlabel('Estimated time to threshold (years)'),ylabel('Value')
    end
    
    % save
    opath = fullfile(PATH_OUTPUT, sprintf('%s_SILA_estimates.csv', base));
    writetable(output, opath);
end