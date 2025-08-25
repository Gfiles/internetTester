document.addEventListener('DOMContentLoaded', () => {
    const timeFrameSelect = document.getElementById('time-frame');
    const combinedChartCanvas = document.getElementById('combinedChart').getContext('2d');

    let combinedChart;

    // Function to fetch data from the backend
    async function fetchData(timeFrame) {
        try {
            const response = await fetch(`/api/network_data?time_frame=${timeFrame}`);
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            return await response.json();
        } catch (error) {
            console.error('Error fetching network data:', error);
            return [];
        }
    }

    // Function to render the combined chart
    function renderChart(data) {
        // Destroy existing chart if it exists
        if (combinedChart) {
            combinedChart.destroy();
        }

        const timeSeries = data.time_series;
        const medians = data.medians;

        const timestamps = timeSeries.map(item => new Date(item.timestamp));
        const downloads = timeSeries.map(item => item.download_mbps);
        const uploads = timeSeries.map(item => item.upload_mbps);
        const latencies = timeSeries.map(item => item.latency_ms);

        const chartDatasets = [
            {
                label: 'Download Speed (Mbps)',
                data: downloads,
                borderColor: 'rgb(75, 192, 192)',
                yAxisID: 'y-speed',
                tension: 0.1,
                fill: false
            },
            {
                label: 'Upload Speed (Mbps)',
                data: uploads,
                borderColor: 'rgb(255, 99, 132)',
                yAxisID: 'y-speed',
                tension: 0.1,
                fill: false
            },
            {
                label: 'Latency (ms)',
                data: latencies,
                borderColor: 'rgb(54, 162, 235)',
                yAxisID: 'y-latency',
                tension: 0.1,
                fill: false
            }
        ];

        // Conditionally add median lines
        if (appSettings.show_median_lines && timestamps.length > 0) {
            if (medians.download !== null) {
                chartDatasets.push({
                    label: 'Median Download (Mbps)',
                    data: Array(timestamps.length).fill(medians.download),
                    borderColor: 'rgba(75, 192, 192, 0.5)',
                    yAxisID: 'y-speed',
                    borderDash: [5, 5], // Dashed line
                    pointRadius: 0, // No points on the line
                    fill: false
                });
            }
            if (medians.upload !== null) {
                chartDatasets.push({
                    label: 'Median Upload (Mbps)',
                    data: Array(timestamps.length).fill(medians.upload),
                    borderColor: 'rgba(255, 99, 132, 0.5)',
                    yAxisID: 'y-speed',
                    borderDash: [5, 5],
                    pointRadius: 0,
                    fill: false
                });
            }
            if (medians.ping !== null) {
                chartDatasets.push({
                    label: 'Median Latency (ms)',
                    data: Array(timestamps.length).fill(medians.ping),
                    borderColor: 'rgba(54, 162, 235, 0.5)',
                    yAxisID: 'y-latency',
                    borderDash: [5, 5],
                    pointRadius: 0,
                    fill: false
                });
            }
        }

        combinedChart = new Chart(combinedChartCanvas, {
            type: 'line',
            data: {
                labels: timestamps,
                datasets: chartDatasets
            },
            options: {
                scales: {
                    x: {
                        type: 'time',
                        time: {
                            unit: 'hour',
                            tooltipFormat: 'MMM d, H:mm:ss'
                        },
                        title: {
                            display: true,
                            text: 'Time'
                        }
                    },
                    'y-speed': {
                        type: 'linear',
                        position: 'left',
                        title: {
                            display: true,
                            text: 'Speed (Mbps)'
                        },
                        beginAtZero: true
                    },
                    'y-latency': {
                        type: 'linear',
                        position: 'right',
                        title: {
                            display: true,
                            text: 'Latency (ms)'
                        },
                        beginAtZero: true,
                        // Hide grid lines for this axis to avoid clutter
                        grid: {
                            drawOnChartArea: false,
                        }
                    }
                },
                plugins: {
                    tooltip: {
                        // Filter out tooltips for median lines
                        filter: function(tooltipItem) {
                            return !tooltipItem.dataset.label.includes('Median');
                        },
                        callbacks: {
                            title: function(context) {
                                return new Date(context[0].label).toLocaleString();
                            }
                        }
                    }
                }
            }
        });
    }

    // Function to fetch and render data, respecting the current time frame
    async function refreshData() {
        const selectedTimeFrame = timeFrameSelect.value;
        console.log(`Refreshing data for time frame: ${selectedTimeFrame}...`);
        const data = await fetchData(selectedTimeFrame);
        renderChart(data);
    }

    // Event listener for time frame selection
    timeFrameSelect.addEventListener('change', refreshData);

    // Initial data load
    refreshData();

    // Set an interval to automatically refresh the data every 5 minutes
    const FIVE_MINUTES_IN_MS = 5 * 60 * 1000;
    setInterval(refreshData, FIVE_MINUTES_IN_MS);
});