/**
 * 可愛貪食蛇遊戲 - 主程式
 * 
 * 特色：
 * - 可愛粉色系蛇蛇帶有表情
 * - 甜點食物（草莓、蛋糕、餅乾等）
 * - 流暢動畫效果
 */

// ===== 遊戲常數 =====
const GRID_SIZE = 20;        // 格子大小
let gameSpeed = 150;         // 遊戲速度 (ms), 預設正常
const CANVAS_SIZE = 400;     // Canvas 尺寸
const GRID_COUNT = CANVAS_SIZE / GRID_SIZE;  // 格子數量

// 可愛的食物表情符號
const FOOD_EMOJIS = ['🍓', '🍰', '🍪', '🍩', '🧁', '🍭', '🍬', '💖', '⭐', '🌸'];

// ===== 遊戲元素 =====
const canvas = document.getElementById('gameCanvas');
const ctx = canvas.getContext('2d');
const scoreElement = document.getElementById('score');
const highScoreElement = document.getElementById('highScore');
const gameOverlay = document.getElementById('gameOverlay');
const overlayTitle = document.getElementById('overlayTitle');
const overlayMessage = document.getElementById('overlayMessage');
const startBtn = document.getElementById('startBtn');
const speedBtns = document.querySelectorAll('.speed-btn');

// ===== 遊戲狀態 =====
let snake = [];
let food = null;
let direction = { x: 1, y: 0 };
let nextDirection = { x: 1, y: 0 };
let score = 0;
let highScore = localStorage.getItem('cuteSnakeHighScore') || 0;
let gameRunning = false;
let gameLoop = null;

// 初始化最高分
highScoreElement.textContent = highScore;

// ===== 蛇的顏色 =====
const SNAKE_COLORS = {
    head: '#FF8FAB',
    headDark: '#FF5C8A',
    body: '#FFB6C8',
    bodyDark: '#FF9BB3',
    blush: '#FF6B8A',
    eye: '#5D4E6D',
    eyeWhite: '#FFFFFF'
};

// ===== 遊戲初始化 =====
function initGame() {
    // 初始化蛇（從中間開始）
    const startX = Math.floor(GRID_COUNT / 2);
    const startY = Math.floor(GRID_COUNT / 2);
    snake = [
        { x: startX, y: startY },
        { x: startX - 1, y: startY },
        { x: startX - 2, y: startY }
    ];

    // 重置方向
    direction = { x: 1, y: 0 };
    nextDirection = { x: 1, y: 0 };

    // 重置分數
    score = 0;
    scoreElement.textContent = score;

    // 生成食物
    spawnFood();

    // 開始遊戲
    gameRunning = true;
    gameOverlay.classList.add('hidden');

    // 開始遊戲迴圈
    if (gameLoop) clearInterval(gameLoop);
    gameLoop = setInterval(update, gameSpeed);
}

// ===== 速度選擇控制 =====
speedBtns.forEach(btn => {
    btn.addEventListener('click', () => {
        // 移除所有 active 狀態
        speedBtns.forEach(b => b.classList.remove('active'));
        // 設定當前按鈕為 active
        btn.classList.add('active');
        // 更新速度
        gameSpeed = parseInt(btn.dataset.speed);
    });
});

// ===== 生成食物 =====
function spawnFood() {
    let validPosition = false;
    let newFood;

    while (!validPosition) {
        newFood = {
            x: Math.floor(Math.random() * GRID_COUNT),
            y: Math.floor(Math.random() * GRID_COUNT),
            emoji: FOOD_EMOJIS[Math.floor(Math.random() * FOOD_EMOJIS.length)]
        };

        // 確保食物不會生成在蛇身上
        validPosition = !snake.some(segment =>
            segment.x === newFood.x && segment.y === newFood.y
        );
    }

    food = newFood;
}

// ===== 遊戲更新 =====
function update() {
    if (!gameRunning) return;

    // 更新方向
    direction = { ...nextDirection };

    // 計算新的頭部位置
    const head = {
        x: snake[0].x + direction.x,
        y: snake[0].y + direction.y
    };

    // 檢查碰撞
    if (checkCollision(head)) {
        gameOver();
        return;
    }

    // 移動蛇
    snake.unshift(head);

    // 檢查是否吃到食物
    if (head.x === food.x && head.y === food.y) {
        eatFood();
    } else {
        snake.pop();  // 如果沒吃到食物，移除尾巴
    }

    // 繪製畫面
    draw();
}

// ===== 碰撞檢測 =====
function checkCollision(head) {
    // 撞牆
    if (head.x < 0 || head.x >= GRID_COUNT ||
        head.y < 0 || head.y >= GRID_COUNT) {
        return true;
    }

    // 撞到自己
    return snake.some((segment, index) =>
        index !== 0 && segment.x === head.x && segment.y === head.y
    );
}

// ===== 吃食物 =====
function eatFood() {
    score += 10;
    scoreElement.textContent = score;

    // 更新最高分
    if (score > highScore) {
        highScore = score;
        highScoreElement.textContent = highScore;
        localStorage.setItem('cuteSnakeHighScore', highScore);
    }

    // 播放吃食物動畫
    canvas.classList.add('eat-animation');
    setTimeout(() => canvas.classList.remove('eat-animation'), 200);

    // 生成新食物
    spawnFood();
}

// ===== 遊戲結束 =====
function gameOver() {
    gameRunning = false;
    clearInterval(gameLoop);

    // 播放遊戲結束動畫
    canvas.classList.add('game-over-animation');
    setTimeout(() => canvas.classList.remove('game-over-animation'), 500);

    // 顯示遊戲結束畫面
    overlayTitle.textContent = '😢 遊戲結束';
    overlayMessage.innerHTML = `你的分數是 <strong>${score}</strong> 分！<br>再試一次吧～`;
    startBtn.innerHTML = '<span>重新開始 💪</span>';
    gameOverlay.classList.remove('hidden');
}

// ===== 繪製畫面 =====
function draw() {
    // 清除畫面
    ctx.fillStyle = '#FFF9FB';
    ctx.fillRect(0, 0, CANVAS_SIZE, CANVAS_SIZE);

    // 繪製格子背景
    drawGrid();

    // 繪製食物
    drawFood();

    // 繪製蛇
    drawSnake();
}

// ===== 繪製格子背景 =====
function drawGrid() {
    ctx.strokeStyle = 'rgba(255, 143, 171, 0.1)';
    ctx.lineWidth = 1;

    for (let i = 0; i <= GRID_COUNT; i++) {
        // 垂直線
        ctx.beginPath();
        ctx.moveTo(i * GRID_SIZE, 0);
        ctx.lineTo(i * GRID_SIZE, CANVAS_SIZE);
        ctx.stroke();

        // 水平線
        ctx.beginPath();
        ctx.moveTo(0, i * GRID_SIZE);
        ctx.lineTo(CANVAS_SIZE, i * GRID_SIZE);
        ctx.stroke();
    }
}

// ===== 繪製食物 =====
function drawFood() {
    const x = food.x * GRID_SIZE + GRID_SIZE / 2;
    const y = food.y * GRID_SIZE + GRID_SIZE / 2;

    // 繪製食物光暈
    const gradient = ctx.createRadialGradient(x, y, 0, x, y, GRID_SIZE);
    gradient.addColorStop(0, 'rgba(255, 215, 0, 0.3)');
    gradient.addColorStop(1, 'rgba(255, 215, 0, 0)');
    ctx.fillStyle = gradient;
    ctx.fillRect(food.x * GRID_SIZE - 5, food.y * GRID_SIZE - 5,
        GRID_SIZE + 10, GRID_SIZE + 10);

    // 繪製食物表情符號
    ctx.font = '16px Arial';
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    ctx.fillText(food.emoji, x, y);
}

// ===== 繪製蛇 =====
function drawSnake() {
    snake.forEach((segment, index) => {
        const x = segment.x * GRID_SIZE;
        const y = segment.y * GRID_SIZE;

        if (index === 0) {
            // 繪製蛇頭
            drawSnakeHead(x, y);
        } else {
            // 繪製蛇身
            drawSnakeBody(x, y, index);
        }
    });
}

// ===== 繪製蛇頭 =====
function drawSnakeHead(x, y) {
    const centerX = x + GRID_SIZE / 2;
    const centerY = y + GRID_SIZE / 2;
    const radius = GRID_SIZE / 2 - 1;

    // 蛇頭主體
    const gradient = ctx.createRadialGradient(
        centerX - 3, centerY - 3, 0,
        centerX, centerY, radius
    );
    gradient.addColorStop(0, SNAKE_COLORS.head);
    gradient.addColorStop(1, SNAKE_COLORS.headDark);

    ctx.fillStyle = gradient;
    ctx.beginPath();
    ctx.arc(centerX, centerY, radius, 0, Math.PI * 2);
    ctx.fill();

    // 計算眼睛位置（根據移動方向）
    const eyeOffset = 4;
    let eye1X, eye1Y, eye2X, eye2Y;

    if (direction.x === 1) {  // 向右
        eye1X = centerX + 2; eye1Y = centerY - eyeOffset;
        eye2X = centerX + 2; eye2Y = centerY + eyeOffset;
    } else if (direction.x === -1) {  // 向左
        eye1X = centerX - 2; eye1Y = centerY - eyeOffset;
        eye2X = centerX - 2; eye2Y = centerY + eyeOffset;
    } else if (direction.y === -1) {  // 向上
        eye1X = centerX - eyeOffset; eye1Y = centerY - 2;
        eye2X = centerX + eyeOffset; eye2Y = centerY - 2;
    } else {  // 向下
        eye1X = centerX - eyeOffset; eye1Y = centerY + 2;
        eye2X = centerX + eyeOffset; eye2Y = centerY + 2;
    }

    // 眼白
    ctx.fillStyle = SNAKE_COLORS.eyeWhite;
    ctx.beginPath();
    ctx.arc(eye1X, eye1Y, 3, 0, Math.PI * 2);
    ctx.arc(eye2X, eye2Y, 3, 0, Math.PI * 2);
    ctx.fill();

    // 眼珠
    ctx.fillStyle = SNAKE_COLORS.eye;
    ctx.beginPath();
    ctx.arc(eye1X + direction.x, eye1Y + direction.y, 1.5, 0, Math.PI * 2);
    ctx.arc(eye2X + direction.x, eye2Y + direction.y, 1.5, 0, Math.PI * 2);
    ctx.fill();

    // 腮紅
    ctx.fillStyle = SNAKE_COLORS.blush;
    ctx.globalAlpha = 0.5;
    ctx.beginPath();
    if (direction.x !== 0) {
        ctx.arc(centerX - direction.x * 3, centerY - 4, 2.5, 0, Math.PI * 2);
        ctx.arc(centerX - direction.x * 3, centerY + 4, 2.5, 0, Math.PI * 2);
    } else {
        ctx.arc(centerX - 4, centerY - direction.y * 3, 2.5, 0, Math.PI * 2);
        ctx.arc(centerX + 4, centerY - direction.y * 3, 2.5, 0, Math.PI * 2);
    }
    ctx.fill();
    ctx.globalAlpha = 1;
}

// ===== 繪製蛇身 =====
function drawSnakeBody(x, y, index) {
    const centerX = x + GRID_SIZE / 2;
    const centerY = y + GRID_SIZE / 2;
    const radius = GRID_SIZE / 2 - 2;

    // 身體漸層
    const gradient = ctx.createRadialGradient(
        centerX - 2, centerY - 2, 0,
        centerX, centerY, radius
    );

    // 根據位置調整顏色深淺，越靠近尾巴越淺
    const alpha = 1 - (index / snake.length) * 0.3;
    gradient.addColorStop(0, `rgba(255, 182, 200, ${alpha})`);
    gradient.addColorStop(1, `rgba(255, 155, 179, ${alpha})`);

    ctx.fillStyle = gradient;
    ctx.beginPath();
    ctx.arc(centerX, centerY, radius, 0, Math.PI * 2);
    ctx.fill();

    // 身體上的愛心裝飾
    if (index % 3 === 0) {
        ctx.font = '8px Arial';
        ctx.fillStyle = 'rgba(255, 255, 255, 0.6)';
        ctx.textAlign = 'center';
        ctx.textBaseline = 'middle';
        ctx.fillText('♡', centerX, centerY);
    }
}

// ===== 鍵盤控制 =====
document.addEventListener('keydown', (e) => {
    if (!gameRunning) return;

    switch (e.key) {
        case 'ArrowUp':
            if (direction.y !== 1) {
                nextDirection = { x: 0, y: -1 };
            }
            break;
        case 'ArrowDown':
            if (direction.y !== -1) {
                nextDirection = { x: 0, y: 1 };
            }
            break;
        case 'ArrowLeft':
            if (direction.x !== 1) {
                nextDirection = { x: -1, y: 0 };
            }
            break;
        case 'ArrowRight':
            if (direction.x !== -1) {
                nextDirection = { x: 1, y: 0 };
            }
            break;
    }

    // 防止方向鍵捲動頁面
    if (['ArrowUp', 'ArrowDown', 'ArrowLeft', 'ArrowRight'].includes(e.key)) {
        e.preventDefault();
    }
});

// ===== 觸控控制（手機） =====
document.getElementById('upBtn')?.addEventListener('click', () => {
    if (gameRunning && direction.y !== 1) {
        nextDirection = { x: 0, y: -1 };
    }
});

document.getElementById('downBtn')?.addEventListener('click', () => {
    if (gameRunning && direction.y !== -1) {
        nextDirection = { x: 0, y: 1 };
    }
});

document.getElementById('leftBtn')?.addEventListener('click', () => {
    if (gameRunning && direction.x !== 1) {
        nextDirection = { x: -1, y: 0 };
    }
});

document.getElementById('rightBtn')?.addEventListener('click', () => {
    if (gameRunning && direction.x !== -1) {
        nextDirection = { x: 1, y: 0 };
    }
});

// ===== 開始按鈕 =====
startBtn.addEventListener('click', initGame);

// ===== 空白鍵開始/重新開始 =====
document.addEventListener('keydown', (e) => {
    if (e.code === 'Space' && !gameRunning) {
        initGame();
    }
});

// ===== 初始繪製 =====
function drawInitialScreen() {
    ctx.fillStyle = '#FFF9FB';
    ctx.fillRect(0, 0, CANVAS_SIZE, CANVAS_SIZE);
    drawGrid();

    // 繪製一條靜態的可愛蛇
    const demoSnake = [
        { x: 10, y: 10 },
        { x: 9, y: 10 },
        { x: 8, y: 10 },
        { x: 7, y: 10 },
        { x: 6, y: 10 }
    ];

    snake = demoSnake;
    direction = { x: 1, y: 0 };
    drawSnake();

    // 繪製一個食物
    food = { x: 13, y: 10, emoji: '🍓' };
    drawFood();
}

// 頁面載入時繪製初始畫面
drawInitialScreen();
