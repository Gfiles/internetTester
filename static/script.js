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

        const timestamps = data.map(item => new Date(item.timestamp));
        const downloads = data.map(item => item.download_mbps);
        const uploads = data.map(item => item.upload_mbps);
        const latencies = data.map(item => item.latency_ms);

        combinedChart = new Chart(combinedChartCanvas, {
            type: 'line',
            data: {
                labels: timestamps,
                datasets: [
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
                ]
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

    // Event listener for time frame selection
    timeFrameSelect.addEventListener('change', async (event) => {
        const selectedTimeFrame = event.target.value;
        const data = await fetchData(selectedTimeFrame);
        renderChart(data);
    });

    // Initial data load and chart render
    async function init() {
        const initialData = await fetchData(timeFrameSelect.value);
        renderChart(initialData);
    }

    init();
});
