const API_BASE_URL = 'http://127.0.0.1:8000'; // Define your API base URL

// 基金列表查询
document.getElementById('fundForm').addEventListener('submit', async (e) => {
    console.log("Fund form submit event triggered!");
    e.preventDefault();
    const fundType = document.getElementById('fundType').value;
    const url = `${API_BASE_URL}/funds${fundType ? `?fund_type=${fundType}` : ''}`; // Use absolute URL
    try {
        const response = await fetch(url);
        const result = await response.json();
        displayFunds(result.data);
    } catch (error) {
        console.error('Error:', error);
    }
});

const MAX_FUNDS_TO_SHOW = 10; // 初始显示的基金数量

function displayFunds(funds) {
    const fundList = document.getElementById('fundList');
    const toggleButton = document.getElementById('toggleFundList');
    fundList.innerHTML = '';

    // 初始显示前 MAX_FUNDS_TO_SHOW 个基金
    const initialFunds = funds.slice(0, MAX_FUNDS_TO_SHOW);
    initialFunds.forEach(fund => {
        const listItem = document.createElement('li');
        listItem.className = 'list-group-item';
        listItem.textContent = fund;
        fundList.appendChild(listItem);
    });

    // 如果基金数量超过 MAX_FUNDS_TO_SHOW，显示"查看更多"按钮
    if (funds.length > MAX_FUNDS_TO_SHOW) {
        toggleButton.style.display = 'block';
        toggleButton.textContent = '查看更多';

        toggleButton.addEventListener('click', () => {
            if (toggleButton.textContent === '查看更多') {
                // 显示剩余基金
                const remainingFunds = funds.slice(MAX_FUNDS_TO_SHOW);
                remainingFunds.forEach(fund => {
                    const listItem = document.createElement('li');
                    listItem.className = 'list-group-item';
                    listItem.textContent = fund;
                    fundList.appendChild(listItem);
                });
                toggleButton.textContent = '收起';
            } else {
                // 收起剩余基金
                const displayedFunds = fundList.querySelectorAll('li');
                displayedFunds.forEach((item, index) => {
                    if (index >= MAX_FUNDS_TO_SHOW) {
                        item.remove();
                    }
                });
                toggleButton.textContent = '查看更多';
            }
        });
    } else {
        toggleButton.style.display = 'none'; // 如果基金数量不足，隐藏按钮
    }
}

// 基金信息查询
document.getElementById('fundInfoForm').addEventListener('submit', async (e) => {
    e.preventDefault();
    const fundCode = document.getElementById('fundCode').value;
    try {
        const response = await fetch(`${API_BASE_URL}/fund/${fundCode}`); // Use absolute URL
        const result = await response.json();
        displayFundInfo(result.data);
    } catch (error) {
        console.error('Error:', error);
    }
});

function displayFundInfo(fundInfo) {
    const fundInfoContent = document.getElementById('fundInfoContent');
    const toggleButton = document.getElementById('toggleFundInfo');

    // 缩略信息
    const summary = {
        '基金代码': fundInfo.fund_code,
        '基金名称': fundInfo.fund_name,
        '基金类型': fundInfo.fund_type,
        '基金经理': fundInfo.manager
    };

    // 完整信息
    const fullInfo = fundInfo;

    // 初始显示缩略信息
    fundInfoContent.textContent = JSON.stringify(summary, null, 2);
    toggleButton.textContent = '展开完整信息';

    // 切换显示完整/缩略信息
    toggleButton.addEventListener('click', () => {
        if (toggleButton.textContent === '展开完整信息') {
            fundInfoContent.textContent = JSON.stringify(fullInfo, null, 2);
            toggleButton.textContent = '收起完整信息';
        } else {
            fundInfoContent.textContent = JSON.stringify(summary, null, 2);
            toggleButton.textContent = '展开完整信息';
        }
    });
}

// 组合优化
document.getElementById('optimizeForm').addEventListener('submit', async (e) => {
    e.preventDefault();
    const fundPool = document.getElementById('fundPool').value.split(',');
    const method = document.getElementById('method').value;
    const riskAversion = parseFloat(document.getElementById('riskAversion').value);
    try {
        const response = await fetch(`${API_BASE_URL}/optimize`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                fund_pool: fundPool,
                method: method,
                risk_aversion: riskAversion
            })
        });
        const result = await response.json();
        document.getElementById('optimizeResultContent').textContent = JSON.stringify(result.data, null, 2);
        renderOptimizeChart(result.data); // 绘制图表
    } catch (error) {
        console.error('Error:', error);
    }
});

let optimizeChartInstance = null; // 用于存储 Chart 实例

function renderOptimizeChart(data) {
    const ctx = document.getElementById('optimizeChart').getContext('2d');

    // 检查是否已存在 Chart 实例，如果存在则销毁
    if (optimizeChartInstance) {
        optimizeChartInstance.destroy();
    }

    optimizeChartInstance = new Chart(ctx, { // 创建新的 Chart 实例并赋值给 optimizeChartInstance
        type: 'bar',
        data: {
            labels: Object.keys(data.weights),
            datasets: [{
                label: '权重',
                data: Object.values(data.weights),
                backgroundColor: 'rgba(54, 162, 235, 0.2)',
                borderColor: 'rgba(54, 162, 235, 1)',
                borderWidth: 1
            }]
        },
        options: {
            scales: {
                y: {
                    beginAtZero: true
                }
            }
        }
    });
}

// 回测
document.getElementById('backtestForm').addEventListener('submit', async (e) => {
    e.preventDefault();
    const fundPool = document.getElementById('backtestFundPool').value.split(',');
    const startDate = document.getElementById('startDate').value;
    const endDate = document.getElementById('endDate').value;
    const backtestLoading = document.getElementById('backtestLoading'); // 获取加载指示器元素

    backtestLoading.style.display = 'block'; // 显示加载指示器

    try {
        const response = await fetch(`${API_BASE_URL}/backtest`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                fund_pool: fundPool,
                start_date: startDate,
                end_date: endDate
            })
        });
        const result = await response.json();
        document.getElementById('backtestResultContent').textContent = JSON.stringify(result.data, null, 2);
        renderBacktestChart(result.data); // 绘制图表
    } catch (error) {
        console.error('Error:', error);
    } finally {
        backtestLoading.style.display = 'none'; // 隐藏加载指示器 (无论成功或失败都隐藏)
    }
});

function renderBacktestChart(data) {
    const ctx = document.getElementById('backtestChart').getContext('2d');
    const originalPortfolioValue = data.portfolio_value;
    let sampledPortfolioValue = [];
    const sampleInterval = 7; // 每隔 7 天取一个数据点

    for (let i = 0; i < originalPortfolioValue.length; i += sampleInterval) {
        sampledPortfolioValue.push(originalPortfolioValue[i]);
    }

    console.log('Original data length:', originalPortfolioValue.length);
    console.log('Sampled data length:', sampledPortfolioValue.length);

    new Chart(ctx, {
        type: 'line',
        data: {
            labels: sampledPortfolioValue.map(entry => entry.date),
            datasets: [{
                label: '组合净值 (抽样)',
                data: sampledPortfolioValue.map(entry => entry.value),
                borderColor: 'rgba(75, 192, 192, 1)',
                fill: false
            }]
        },
        options: {
            scales: {
                x: {
                    type: 'time',
                    time: {
                        unit: 'day'
                    }
                },
                y: {
                    beginAtZero: true
                }
            }
        }
    });
} 