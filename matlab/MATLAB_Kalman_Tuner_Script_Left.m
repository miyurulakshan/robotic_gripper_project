function matlab_left_claw_tuner()
% MATLAB Interactive Script for Manual Kalman Filter Tuning of the LEFT CLAW

clear; clc;

% --- 1. Load Data ---
disp('Please select your gripper_kalman_log.csv file...');
[file, path] = uigetfile('*.csv');
if isequal(file, 0), disp('Selection cancelled.'); return; end
full_path = fullfile(path, file);
disp(['Loading file: ', full_path]);
data_table = readtable(full_path);

% --- 2. Extract Left Claw Data ---
time_vector = data_table.Time;
% FSRs 1-4 are the left claw
fsr_signals_left = table2array(data_table(:, 4:7)); 

% --- 3. Create the Interactive Figure ---
fig = figure('Name', 'Interactive Kalman Tuner - LEFT CLAW', 'NumberTitle', 'off', 'WindowState', 'maximized');
ax = axes('Parent', fig, 'Position', [0.1 0.35 0.85 0.55]);
hold(ax, 'on');
grid(ax, 'on');
title(ax, 'Left Claw Kalman Filter Performance');
xlabel(ax, 'Time (s)');
ylabel(ax, 'Force (ADC Value)');

% Plot raw FSR data
p_fsr = gobjects(4, 1);
colors = lines(4);
for i = 1:4
    p_fsr(i) = plot(ax, time_vector, fsr_signals_left(:, i), ':', 'LineWidth', 1.5, 'Color', colors(i,:), 'DisplayName', ['FSR ' num2str(i)]);
end

% Plot filtered output
p_filtered = plot(ax, time_vector, zeros(size(time_vector)), 'b-', 'LineWidth', 2.0, 'DisplayName', 'Kalman Filtered Output');
legend(ax, 'show', 'Location', 'eastoutside');

% --- 4. Add UI Controls ---
% Q Slider
q_slider = uicontrol('Parent', fig, 'Style', 'slider', 'Units', 'normalized', ...
    'Position', [0.1 0.2 0.8 0.03], 'Min', -6, 'Max', -1, 'Value', -4, ...
    'Callback', @(s, e) update_plot());
q_label = uicontrol('Parent', fig, 'Style', 'text', 'Units', 'normalized', ...
    'Position', [0.1 0.23 0.8 0.03], 'String', 'Process Noise (Q_left)');

% R Sliders (one for each sensor)
r_sliders = gobjects(4, 1);
r_labels = gobjects(4, 1);
slider_y_pos = 0.12;
for i = 1:4
    r_sliders(i) = uicontrol('Parent', fig, 'Style', 'slider', 'Units', 'normalized', ...
        'Position', [0.1 + (i-1)*0.2, slider_y_pos, 0.18, 0.03], 'Min', -2, 'Max', 3, 'Value', 0, ...
        'Callback', @(s, e) update_plot());
    r_labels(i) = uicontrol('Parent', fig, 'Style', 'text', 'Units', 'normalized', ...
        'Position', [0.1 + (i-1)*0.2, slider_y_pos+0.03, 0.18, 0.03], 'String', ['R_left(' num2str(i) ')']);
end

% --- MODIFIED: Add checkboxes to enable/disable sensors ---
sensor_checkboxes = gobjects(4, 1);
uicontrol('Parent', fig, 'Style', 'text', 'Units', 'normalized', 'Position', [0.01 0.9 0.08 0.03], 'String', 'Enable Sensors:', 'FontWeight', 'bold');
y_pos = 0.86;
for i = 1:4
    sensor_checkboxes(i) = uicontrol('Parent', fig, 'Style', 'checkbox', 'String', ['FSR ' num2str(i)], ...
        'Value', 1, 'Units', 'normalized', 'Position', [0.01 y_pos 0.08 0.03], 'Callback', @(s, e) update_plot());
    y_pos = y_pos - 0.04;
end

% Text box to display the final Python code
py_code_display = uicontrol('Parent', fig, 'Style', 'text', 'Units', 'normalized', ...
    'Position', [0.1 0.02 0.8 0.05], 'String', 'Your Python code will appear here.', ...
    'FontSize', 10, 'FontName', 'Courier New', 'BackgroundColor', [0.95 0.95 0.95]);

% Initial plot update
update_plot();

% --- Helper Functions ---
    function update_plot()
        % Get Q value
        Q_val = 10^q_slider.Value;
        
        % Get all 4 R values
        R_diag_full = zeros(1, 4);
        for i = 1:4
            R_diag_full(i) = 10^r_sliders(i).Value;
            r_labels(i).String = ['R_left(' num2str(i) '): ' num2str(R_diag_full(i), '%.e')];
        end
        q_label.String = ['Process Noise (Q_left): ', num2str(Q_val, '%.e')];
        
        % --- MODIFIED: Determine which sensors are active ---
        active_sensors_idx = find([sensor_checkboxes.Value]);
        if isempty(active_sensors_idx)
            p_filtered.YData = nan(size(time_vector)); % Show nothing if no sensors selected
            py_code_display.String = 'No sensors selected. Please enable at least one sensor.';
            return;
        end
        
        % Filter data and R values for active sensors
        active_data = fsr_signals_left(:, active_sensors_idx);
        active_R_diag = R_diag_full(active_sensors_idx);
        
        % Run simulation
        filtered_output = run_kalman_simulation(active_data, Q_val, active_R_diag);
        
        % Update the plot data
        p_filtered.YData = filtered_output;
        
        % Update the Python code display
        py_code_str = sprintf('Q_left = np.array([[%.e]])\nR_left = np.diag([%.4f, %.4f, %.4f, %.4f])', ...
            Q_val, R_diag_full(1), R_diag_full(2), R_diag_full(3), R_diag_full(4));
        py_code_display.String = {py_code_str, ['Note: Currently simulating with ' num2str(length(active_sensors_idx)) ' active sensor(s).']};
        
        drawnow;
    end

    function [filtered_output] = run_kalman_simulation(data, Q_val, R_diag)
        num_samples = size(data, 1);
        num_sensors = size(data, 2);
        filtered_output = zeros(num_samples, 1);
        
        % --- MODIFIED: Dynamically set H matrix ---
        A = 1;
        H = ones(num_sensors, 1);
        Q = Q_val;
        R = diag(R_diag);
        x_hat = mean(data(1,:));
        P = 100;
        I = 1;

        for k = 1:num_samples
            x_hat_minus = A * x_hat;
            P_minus = A * P * A' + Q;
            
            K = (P_minus * H') / (H * P_minus * H' + R);
            z = data(k, :)';
            x_hat = x_hat_minus + K * (z - H * x_hat_minus);
            P = (I - K * H) * P_minus;
            
            filtered_output(k) = x_hat;
        end
    end
end
