close all; clear all; clc;

RP=actxserver('RPco.x');

if RP.ConnectRZ5('GB',1)==0 disp 'Error connecting to RZ5'; end
RP.ClearCOF();
if RP.LoadCOF('physiology_test_v2.rcx')==0 disp 'Error loading circuit'; end 
RP.Run;
if bitget(RP.GetStatus,1:3)~= [1 1 1] disp 'Error, circuit not running'; 
else disp 'Circuit running'; 
end;

tests = repmat([1 2 3], 1, 10000);

ave1 = 0;
for i = 1:length(tests)
    tic
    RP.SendParTable('Maps', tests(i)-1);
    %disp(['map ' num2str(tests(i)) ': ' num2str(RP.ReadTagV('diff_map', 0, 16))])
    ave1 = ave1 + toc;
end

%matrix = zeros(3,16);
%matrix(1,:) = [1  0  0  0  0 -1  0  0  0  0  0  0  0  0  0  0];
%matrix(2,:) = [1  0  0  0  0  1  0  0  0  0  0  0  0  0  0  0];
%matrix(3,:) = [3  3  3  3  3  3  3  3  3  3  3  3  3  3  3  3];

matrix = zeros(3,64);
matrix(1,:) = repmat([1  0  0  0  0 -1  0  0  0  0  0  0  0  0  0  0],1,4);
matrix(2,:) = repmat([1  0  0  0  0  1  0  0  0  0  0  0  0  0  0  0],1,4);
matrix(3,:) = repmat([3  3  3  3  3  3  3  3  3  3  3  3  3  3  3  3],1,4);

ave = 0;
for i = 1:length(tests)
    tic
    matrix(tests(i),:)
    RP.WriteTagV('diff_map', 0, matrix(tests(i),:));
    %disp(['map ' num2str(tests(i)) ': ' num2str(RP.ReadTagV('diff_map', 0, 16))])
    ave2 = ave2 + toc;
end

disp(['average time: ' num2str(1000*ave1/length(tests))])
disp(['average time: ' num2str(1000*ave2/length(tests))])

RP.Halt;

