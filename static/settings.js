document.addEventListener('DOMContentLoaded', () => {
    const settingsForm = document.getElementById('settings-form');
    const portInput = document.getElementById('port');
    const originalPort = portInput.value;

    settingsForm.addEventListener('submit', async (event) => {
        event.preventDefault();
        const newPort = portInput.value;

        const settings = {
            port: parseInt(newPort, 10),
            test_interval_minutes: parseInt(document.getElementById('test_interval_minutes').value, 10),
            open_on_startup: document.getElementById('open_on_startup').checked,
            show_median_lines: document.getElementById('show_median_lines').checked,
            default_time_frame: document.getElementById('default_time_frame').value
        };

        try {
            const response = await fetch('/api/settings', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(settings),
            });

            const result = await response.json();

            if (response.ok) {
                let message = "Settings saved successfully.";
                if (newPort !== originalPort) {
                    message += "\n\nPlease restart the application for the port change to take effect.";
                }
                alert(message);
                if (newPort === originalPort) { // Only reload if port hasn't changed
                    window.location.reload();
                }
            } else {
                throw new Error(result.message || 'Failed to save settings.');
            }
        } catch (error) {
            console.error('Error saving settings:', error);
            alert(`Error saving settings: ${error.message}`);
        }
    });
});