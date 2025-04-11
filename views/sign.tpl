<!DOCTYPE html>
<html>
<head>
    <title>Transaction Analysis</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
    <script src="https://unpkg.com/htmx.org@2.0.4"></script>
    <script src="https://unpkg.com/htmx-ext-sse@2.2.2"></script>
    <style>
        .transaction-info {
            background-color: #f8f9fa;
            padding: 20px;
            border-radius: 8px;
            margin-bottom: 20px;
        }
        .analysis-section {
            background-color: #e9ecef;
            padding: 20px;
            border-radius: 8px;
        }
        .info-item {
            margin-bottom: 15px;
        }
        .info-label {
            font-weight: bold;
            margin-right: 10px;
        }
        .data-content {
            word-wrap: break-word;
            word-break: break-all;
            max-height: 100px;
            overflow: hidden;
            position: relative;
            padding: 10px;
            background: #f8f9fa;
            border-radius: 4px;
            transition: max-height 0.3s ease-out;
        }
        .data-content.expanded {
            max-height: none;
        }
        .expand-btn {
            display: block;
            margin-top: 5px;
            color: #0d6efd;
            cursor: pointer;
            user-select: none;
        }
        .risk-alert {
            padding: 15px;
            border-radius: 8px;
            margin-bottom: 20px;
            text-align: center;
            font-weight: bold;
            font-size: 1.2em;
        }
        .risk-alert.danger {
            background-color: #dc3545;
            color: white;
        }
        .risk-alert.safe {
            background-color: #198754;
            color: white;
        }
        .loading {
            text-align: center;
            padding: 20px;
        }
        .loading-spinner {
            width: 3rem;
            height: 3rem;
        }
        .step {
            padding: 10px;
            margin-bottom: 10px;
            background-color: #f0f0f0;
            border-radius: 5px;
            border-left: 4px solid #007bff;
        }
    </style>
</head>
<body>
    <div class="container mt-4">
        <h2>Transaction Analysis</h2>
        <div class="row">
            <!-- Left Column: Transaction Information -->
            <div class="col-md-6">
                <div class="transaction-info">
                    <h4>Transaction Details</h4>
                    <div class="info-item">
                        <span class="info-label">Network:</span> {{tx_info['network']}}
                    </div>
                    <div class="info-item">
                        <span class="info-label">From:</span> {{tx_info['from_address']}}
                    </div>
                    <div class="info-item">
                        <span class="info-label">To:</span> {{tx_info['to_address']}}
                    </div>
                    <div class="info-item">
                        <span class="info-label">Data:</span>
                        <div class="data-content" id="dataContent">{{tx_info['data']}}</div>
                        <span class="expand-btn" onclick="toggleData()" id="expandBtn">More</span>
                    </div>
                </div>
            </div>
            
            <!-- Right Column: Analysis -->
            <div class="col-md-6">
                <div class="analysis-section">
                    <h4>Security Analysis</h4>
                    <div id="analysis-content">

                        <div id="analysis-results"  hx-ext="sse"
                             sse-connect="/analysis-stream?tx={{tx_info['tx']}}" 
                             sse-swap="message" 
                             hx-swap="innerHTML">
                            <div class="loading">
                                <div class="spinner-border loading-spinner" role="status">
                                    <span class="visually-hidden">Loading...</span>
                                </div>
                                <p class="mt-3">Analyzing transaction... Please wait.</p>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </div>

    <script>
    function toggleData() {
        const content = document.getElementById('dataContent');
        const btn = document.getElementById('expandBtn');
        
        if (content.classList.contains('expanded')) {
            content.classList.remove('expanded');
            btn.textContent = 'More';
        } else {
            content.classList.add('expanded');
            btn.textContent = 'Less';
        }
    }
    </script>
</body>
</html> 