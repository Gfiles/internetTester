document.addEventListener('DOMContentLoaded', () => {
    const timeFrameSelect = document.getElementById('time-frame');
    const downloadChartCanvas = document.getElementById('downloadChart').getContext('2d');
    const uploadChartCanvas = document.getElementById('uploadChart').getContext('2d');
    const latencyChartCanvas = document.getElementById('latencyChart').getContext('2d');

    let downloadChart;
    let uploadChart;
    let latencyChart;

    // Function to fetch data from the backend
    async function fetchData(timeFrame) {
        try {
            const response = await fetch(`/api/network_data?time_frame=${timeFrame}`);
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            const data = await response.json();
            return data;
        } catch (error) {
            console.error('Error fetching network data:', error);
            return [];
        }
    }

    // Function to render charts
    function renderCharts(data) {
        // Destroy existing charts if they exist
        if (downloadChart) downloadChart.destroy();
        if (uploadChart) uploadChart.destroy();
        if (latencyChart) latencyChart.destroy();

        const timestamps = data.map(item => new Date(item.timestamp));
        const downloads = data.map(item => item.download_mbps);
        const uploads = data.map(item => item.upload_mbps);
        const latencies = data.map(item => item.latency_ms);

        // Create Download Chart
        downloadChart = new Chart(downloadChartCanvas, {
            type: 'line',
            data: {
                labels: timestamps,
                datasets: [{
                    label: 'Download Speed (Mbps)',
                    data: downloads,
                    borderColor: 'rgb(75, 192, 192)',
                    tension: 0.1,
                    fill: false
                }]
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
                    y: {
                        title: {
                            display: true,
                            text: 'Speed (Mbps)'
                        },
                        beginAtZero: true
                    }
                },
                plugins: {
                    tooltip: {
                        callbacks: {
                            title: function(context) {
                                // Format timestamp for tooltip
                                return new Date(context[0].label).toLocaleString();
                            }
                        }
                    }
                }
            }
        });

        // Create Upload Chart
        uploadChart = new Chart(uploadChartCanvas, {
            type: 'line',
            data: {
                labels: timestamps,
                datasets: [{
                    label: 'Upload Speed (Mbps)',
                    data: uploads,
                    borderColor: 'rgb(255, 99, 132)',
                    tension: 0.1,
                    fill: false
                }]
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
                    y: {
                        title: {
                            display: true,
                            text: 'Speed (Mbps)'
                        },
                        beginAtZero: true
                    }
                },
                 plugins: {
                    tooltip: {
                        callbacks: {
                            title: function(context) {
                                // Format timestamp for tooltip
                                return new Date(context[0].label).toLocaleString();
                            }
                        }
                    }
                }
            }
        });

        // Create Latency Chart
        latencyChart = new Chart(latencyChartCanvas, {
            type: 'line',
            data: {
                labels: timestamps,
                datasets: [{
                    label: 'Latency (ms)',
                    data: latencies,
                    borderColor: 'rgb(54, 162, 235)',
                    tension: 0.1,
                     fill: false
                }]
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
                    y: {
                        title: {
                            display: true,
                            text: 'Latency (ms)'
                        },
                        beginAtZero: true
                    }
                },
                 plugins: {
                    tooltip: {
                        callbacks: {
                            title: function(context) {
                                // Format timestamp for tooltip
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
        renderCharts(data);
    });

    // Initial data load and chart render (default to 'day')
    async function init() {
        const initialData = await fetchData(timeFrameSelect.value);
        renderCharts(initialData);
    }

    init();
});