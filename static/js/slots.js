class SlotMachine {
    constructor(containerId, options = {}) {
        this.container = document.getElementById(containerId);
        this.isSpinning = false;
        this.spinDuration = options.duration || 2000;
        this.reelsCount = options.reels || 5;
        this.rowsCount = options.rows || 3;
        this.symbols = [
            { icon: '🍒', name: 'Cherry', value: 2, weight: 20 },
            { icon: '🍋', name: 'Lemon', value: 3, weight: 15 },
            { icon: '🍊', name: 'Orange', value: 4, weight: 12 },
            { icon: '🍇', name: 'Grape', value: 5, weight: 10 },
            { icon: '💎', name: 'Diamond', value: 10, weight: 8 },
            { icon: '7️⃣', name: 'Seven', value: 20, weight: 5 },
            { icon: '🔔', name: 'Bell', value: 15, weight: 6 },
            { icon: '⭐', name: 'Star', value: 12, weight: 7 },
            { icon: '💰', name: 'Money Bag', value: 25, weight: 3 },
            { icon: '👑', name: 'Crown', value: 50, weight: 2 }
        ];
        this.reels = [];
        this.currentResult = null;
        this.winLines = [];
        this.init();
    }
    
    init() {
        this.createSlotMachine();
        this.createControls();
        this.createWinDisplay();
    }
    
    createSlotMachine() {
        this.container.innerHTML = '';
        this.container.className = 'slot-machine';
        
        for (let i = 0; i < this.reelsCount; i++) {
            const reelContainer = document.createElement('div');
            reelContainer.className = 'reel-container';
            reelContainer.dataset.reelIndex = i;
            
            const reel = document.createElement('div');
            reel.className = 'reel';
            
            for (let j = 0; j < this.rowsCount + 4; j++) { 
                const symbol = document.createElement('div');
                symbol.className = 'symbol';
                symbol.textContent = this.getRandomSymbol().icon;
                reel.appendChild(symbol);
            }
            
            reelContainer.appendChild(reel);
            this.container.appendChild(reelContainer);
            
            this.reels.push({
                element: reel,
                container: reelContainer,
                symbols: Array.from(reel.querySelectorAll('.symbol'))
            });
        }
        
        this.createWinLinesOverlay();
    }
    
    createWinLinesOverlay() {
        const overlay = document.createElement('div');
        overlay.className = 'win-lines-overlay';
        overlay.innerHTML = `
            <div class="win-line line-1"></div>
            <div class="win-line line-2"></div>
            <div class="win-line line-3"></div>
            <div class="win-line line-4"></div>
            <div class="win-line line-5"></div>
        `;
        this.container.appendChild(overlay);
    }
    
    createControls() {
        const controls = document.createElement('div');
        controls.className = 'slot-controls';
        controls.innerHTML = `
            <div class="bet-controls">
                <button class="btn bet-btn bet-dec">-</button>
                <input type="number" class="bet-amount" value="1" min="1" max="1000">
                <button class="btn bet-btn bet-inc">+</button>
            </div>
            <button class="btn spin-btn" id="spin-btn">
                <i class="fas fa-play"></i> SPIN
            </button>
            <button class="btn auto-btn" id="auto-btn">
                <i class="fas fa-sync"></i> AUTO
            </button>
            <button class="btn reset-btn" id="reset-btn">
                <i class="fas fa-redo"></i> RESET
            </button>
        `;
        
        this.container.parentNode.appendChild(controls);
        
        document.getElementById('spin-btn').addEventListener('click', () => this.spin());
        document.getElementById('reset-btn').addEventListener('click', () => this.reset());
        document.getElementById('auto-btn').addEventListener('click', () => this.toggleAutoSpin());
        
        const betInput = controls.querySelector('.bet-amount');
        controls.querySelector('.bet-dec').addEventListener('click', () => {
            betInput.value = Math.max(1, parseInt(betInput.value) - 1);
        });
        controls.querySelector('.bet-inc').addEventListener('click', () => {
            betInput.value = Math.min(1000, parseInt(betInput.value) + 1);
        });
    }
    
    createWinDisplay() {
        const display = document.createElement('div');
        display.className = 'win-display';
        display.innerHTML = `
            <div class="win-info">
                <div class="win-amount">$0</div>
                <div class="win-multiplier">Multiplier: x0</div>
            </div>
            <div class="win-lines-container">
                <h4>Winning Lines</h4>
                <div class="win-lines-list"></div>
            </div>
        `;
        
        this.container.parentNode.appendChild(display);
        this.winDisplay = display;
    }
    
    getRandomSymbol() {
        const weightedSymbols = [];
        this.symbols.forEach(symbol => {
            for (let i = 0; i < symbol.weight; i++) {
                weightedSymbols.push(symbol);
            }
        });
        
        return weightedSymbols[Math.floor(Math.random() * weightedSymbols.length)];
    }
    
    async spin(customResult = null) {
        if (this.isSpinning) return;
        
        this.isSpinning = true;
        this.container.classList.add('spinning');
        
        document.getElementById('spin-btn').disabled = true;
        document.getElementById('auto-btn').disabled = true;
        
        this.hideWinLines();
        
        const result = customResult || this.generateRandomResult();
        this.currentResult = result;
        
        const spinPromises = this.reels.map((reel, index) => 
            this.animateReel(reel, result[index], index * 150)
        );
        
        await Promise.all(spinPromises);
        
        await this.sleep(500);
        
        this.winLines = this.calculateWinLines(result);
        
        this.showWinLines();
        
        this.updateWinDisplay();
        
        this.isSpinning = false;
        this.container.classList.remove('spinning');
        document.getElementById('spin-btn').disabled = false;
        document.getElementById('auto-btn').disabled = false;
        
        return {
            result: result,
            winLines: this.winLines,
            totalWin: this.winLines.reduce((sum, line) => sum + line.win, 0)
        };
    }
    
    async animateReel(reel, targetSymbol, delay) {
        await this.sleep(delay);
        
        reel.container.classList.add('reel-spinning');
        
        const fastSpins = 15 + Math.floor(Math.random() * 10);
        let currentSpin = 0;
        
        const fastSpin = () => {
            this.shiftReelUp(reel);
            currentSpin++;
            
            if (currentSpin < fastSpins) {
                requestAnimationFrame(fastSpin);
            } else {
                const slowSpins = 3;
                let slowSpinCount = 0;
                
                const slowSpin = () => {
                    this.shiftReelUp(reel);
                    slowSpinCount++;
                    
                    if (slowSpinCount < slowSpins) {
                        setTimeout(slowSpin, 150);
                    } else {
                        this.setReelPosition(reel, targetSymbol);
                        reel.container.classList.remove('reel-spinning');
                        
                        reel.container.classList.add('reel-stopping');
                        setTimeout(() => {
                            reel.container.classList.remove('reel-stopping');
                        }, 300);
                    }
                };
                
                setTimeout(slowSpin, 100);
            }
        };
        
        fastSpin();
    }
    
    shiftReelUp(reel) {
        const firstSymbol = reel.symbols[0].textContent;
        
        for (let i = 0; i < reel.symbols.length - 1; i++) {
            reel.symbols[i].textContent = reel.symbols[i + 1].textContent;
        }
        
        reel.symbols[reel.symbols.length - 1].textContent = this.getRandomSymbol().icon;
    }
    
    setReelPosition(reel, targetSymbol) {
        const centerIndex = 2; 
        
        const symbolIndex = this.symbols.findIndex(s => s.icon === targetSymbol.icon);
        
        for (let i = 0; i < this.rowsCount; i++) {
            const offset = i - 1; 
            const symbolIdx = (symbolIndex + offset + this.symbols.length) % this.symbols.length;
            reel.symbols[centerIndex + offset].textContent = this.symbols[symbolIdx].icon;
            reel.symbols[centerIndex + offset].className = 'symbol';
            
            if (offset === 0) {
                reel.symbols[centerIndex + offset].dataset.symbol = targetSymbol.icon;
            }
        }
    }
    
    generateRandomResult() {
        const result = [];
        for (let i = 0; i < this.reelsCount; i++) {
            result.push(this.getRandomSymbol());
        }
        return result;
    }
    
    calculateWinLines(result) {
        const lines = [];
        const betAmount = parseInt(document.querySelector('.bet-amount')?.value || 1);
        
        if (result.every(symbol => symbol.icon === result[0].icon)) {
            const multiplier = result[0].value * 100;
            lines.push({
                line: 1,
                symbols: result.map(s => s.icon),
                multiplier: multiplier,
                win: betAmount * multiplier,
                type: 'jackpot'
            });
        }
        
        for (let i = 0; i <= 1; i++) {
            if (result[i].icon === result[i + 1].icon && 
                result[i].icon === result[i + 2].icon && 
                result[i].icon === result[i + 3].icon) {
                const multiplier = result[i].value * 10;
                lines.push({
                    line: 2 + i,
                    symbols: result.slice(i, i + 4).map(s => s.icon),
                    multiplier: multiplier,
                    win: betAmount * multiplier,
                    type: 'four_of_a_kind'
                });
            }
        }
        
        for (let i = 0; i <= 2; i++) {
            if (result[i].icon === result[i + 1].icon && 
                result[i].icon === result[i + 2].icon) {
                const multiplier = result[i].value * 3;
                lines.push({
                    line: 4 + i,
                    symbols: result.slice(i, i + 3).map(s => s.icon),
                    multiplier: multiplier,
                    win: betAmount * multiplier,
                    type: 'three_of_a_kind'
                });
            }
        }
        
        for (let i = 0; i <= 3; i++) {
            if (result[i].icon === result[i + 1].icon) {
                const multiplier = result[i].value;
                lines.push({
                    line: 7 + i,
                    symbols: result.slice(i, i + 2).map(s => s.icon),
                    multiplier: multiplier,
                    win: betAmount * multiplier,
                    type: 'pair'
                });
            }
        }
        
        const specialCombinations = [
            { symbols: ['🍒', '🍒', '🍒', '7️⃣', '7️⃣'], multiplier: 50 },
            { symbols: ['💎', '💎', '💎', '⭐', '⭐'], multiplier: 30 },
            { symbols: ['🔔', '🔔', '🔔', '🔔', '🔔'], multiplier: 100 },
            { symbols: ['👑', '💰', '💎', '⭐', '🔔'], multiplier: 25 }
        ];
        
        specialCombinations.forEach((combo, index) => {
            let matches = 0;
            for (let i = 0; i < 5; i++) {
                if (result[i].icon === combo.symbols[i]) {
                    matches++;
                }
            }
            
            if (matches >= 4) {
                lines.push({
                    line: 11 + index,
                    symbols: result.map(s => s.icon),
                    multiplier: combo.multiplier,
                    win: betAmount * combo.multiplier,
                    type: 'special'
                });
            }
        });
        
        return lines;
    }
    
    showWinLines() {
        this.winLines.forEach(line => {
            const lineElement = this.container.querySelector(`.win-line.line-${line.line}`);
            if (lineElement) {
                lineElement.classList.add('active');
                
                this.highlightWinningSymbols(line);
            }
        });
        
        if (this.winLines.length > 0) {
            this.container.classList.add('win-animation');
            setTimeout(() => {
                this.container.classList.remove('win-animation');
            }, 2000);
        }
    }
    
    hideWinLines() {
        this.container.querySelectorAll('.win-line').forEach(line => {
            line.classList.remove('active');
        });
        
        this.container.querySelectorAll('.symbol.win').forEach(symbol => {
            symbol.classList.remove('win');
        });
    }
    
    highlightWinningSymbols(line) {
        if (line.symbols && line.symbols.length > 0) {
            this.reels.forEach((reel, index) => {
                if (index < line.symbols.length) {
                    const symbols = reel.symbols;
                    const visibleSymbols = symbols.slice(1, 4); 
                    
                    visibleSymbols.forEach(symbol => {
                        if (symbol.textContent === line.symbols[index]) {
                            symbol.classList.add('win');
                        }
                    });
                }
            });
        }
    }
    
    updateWinDisplay() {
        const totalWin = this.winLines.reduce((sum, line) => sum + line.win, 0);
        const betAmount = parseInt(document.querySelector('.bet-amount')?.value || 1);
        
        const winAmountElement = this.winDisplay.querySelector('.win-amount');
        const multiplierElement = this.winDisplay.querySelector('.win-multiplier');
        const linesListElement = this.winDisplay.querySelector('.win-lines-list');
        
        winAmountElement.textContent = `$${totalWin.toFixed(2)}`;
        multiplierElement.textContent = `Multiplier: x${(totalWin / betAmount).toFixed(1)}`;
        
        if (this.winLines.length > 0) {
            linesListElement.innerHTML = this.winLines.map(line => `
                <div class="win-line-item">
                    <div class="line-symbols">
                        ${line.symbols.map(s => `<span class="symbol">${s}</span>`).join('')}
                    </div>
                    <div class="line-info">
                        <span class="line-type">${line.type}</span>
                        <span class="line-win">$${line.win.toFixed(2)} (x${line.multiplier})</span>
                    </div>
                </div>
            `).join('');
        } else {
            linesListElement.innerHTML = '<div class="no-wins">No winning lines</div>';
        }
        
        if (totalWin > 0) {
            winAmountElement.classList.add('win-animation');
            setTimeout(() => {
                winAmountElement.classList.remove('win-animation');
            }, 1000);
        }
    }
    
    reset() {
        this.hideWinLines();
        this.currentResult = null;
        this.winLines = [];
        
        this.winDisplay.querySelector('.win-amount').textContent = '$0';
        this.winDisplay.querySelector('.win-multiplier').textContent = 'Multiplier: x0';
        this.winDisplay.querySelector('.win-lines-list').innerHTML = '<div class="no-wins">No winning lines</div>';
        
        this.reels.forEach(reel => {
            reel.symbols.forEach(symbol => {
                symbol.textContent = this.getRandomSymbol().icon;
                symbol.className = 'symbol';
            });
        });
    }
    
    toggleAutoSpin() {
        const autoBtn = document.getElementById('auto-btn');
        if (this.autoSpinInterval) {
            clearInterval(this.autoSpinInterval);
            this.autoSpinInterval = null;
            autoBtn.innerHTML = '<i class="fas fa-sync"></i> AUTO';
            autoBtn.classList.remove('active');
        } else {
            this.autoSpinInterval = setInterval(() => {
                if (!this.isSpinning) {
                    this.spin();
                }
            }, 3000); 
            autoBtn.innerHTML = '<i class="fas fa-stop"></i> STOP';
            autoBtn.classList.add('active');
        }
    }
    
    sleep(ms) {
        return new Promise(resolve => setTimeout(resolve, ms));
    }
}

document.addEventListener('DOMContentLoaded', function() {
    const slotStyles = `
    /* Slot Machine Container */
    .slot-machine {
        display: flex;
        gap: 10px;
        background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
        padding: 25px;
        border-radius: 20px;
        border: 4px solid #ffd700;
        box-shadow: 
            0 10px 40px rgba(0, 0, 0, 0.6),
            inset 0 0 60px rgba(255, 215, 0, 0.1);
        position: relative;
        overflow: hidden;
        margin-bottom: 20px;
        min-height: 300px;
    }
    
    /* Shine Effect */
    .slot-machine::before {
        content: '';
        position: absolute;
        top: -50%;
        left: -50%;
        width: 200%;
        height: 200%;
        background: linear-gradient(
            to right,
            transparent 20%,
            rgba(255, 215, 0, 0.1) 50%,
            transparent 80%
        );
        animation: shine 3s infinite linear;
        pointer-events: none;
    }
    
    /* Spinning Animation */
    .slot-machine.spinning::after {
        content: '🎰 SPINNING 🎰';
        position: absolute;
        top: 50%;
        left: 50%;
        transform: translate(-50%, -50%);
        font-size: 2.5rem;
        font-weight: bold;
        color: #ffd700;
        text-shadow: 
            0 0 10px #ffd700,
            0 0 20px #ffd700,
            0 0 30px #ffd700;
        z-index: 100;
        animation: spin-text 0.5s infinite alternate;
    }
    
    /* Reel Container */
    .reel-container {
        flex: 1;
        position: relative;
        border-radius: 12px;
        overflow: hidden;
        border: 2px solid rgba(255, 215, 0, 0.3);
        background: rgba(0, 0, 0, 0.7);
        box-shadow: inset 0 0 20px rgba(0, 0, 0, 0.8);
    }
    
    /* Reel */
    .reel {
        position: relative;
        height: 240px;
        display: flex;
        flex-direction: column;
        perspective: 1000px;
    }
    
    /* Reel Spinning Animation */
    .reel-spinning .reel {
        animation: reel-spin 0.1s infinite linear;
    }
    
    .reel-stopping {
        animation: reel-stop 0.3s ease-out;
    }
    
    /* Symbol Styling */
    .symbol {
        flex: 1;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 3.5rem;
        background: linear-gradient(135deg, rgba(255, 255, 255, 0.1), transparent);
        border-bottom: 1px solid rgba(255, 215, 0, 0.2);
        transition: all 0.3s ease;
        position: relative;
        transform-style: preserve-3d;
    }
    
    /* Winning Symbol */
    .symbol.win {
        animation: win-symbol 1s infinite alternate;
        background: linear-gradient(135deg, rgba(255, 215, 0, 0.3), transparent);
        box-shadow: 
            inset 0 0 20px rgba(255, 215, 0, 0.5),
            0 0 30px rgba(255, 215, 0, 0.7);
        border-color: #ffd700;
        transform: scale(1.1);
        z-index: 2;
    }
    
    /* Controls */
    .slot-controls {
        display: flex;
        gap: 15px;
        justify-content: center;
        align-items: center;
        margin: 20px 0;
        padding: 20px;
        background: rgba(0, 0, 0, 0.5);
        border-radius: 15px;
        border: 2px solid rgba(255, 215, 0, 0.3);
    }
    
    .bet-controls {
        display: flex;
        gap: 10px;
        align-items: center;
    }
    
    .bet-amount {
        width: 100px;
        padding: 10px;
        text-align: center;
        font-size: 1.2rem;
        font-weight: bold;
        background: rgba(255, 255, 255, 0.1);
        border: 2px solid #ffd700;
        border-radius: 8px;
        color: white;
    }
    
    .btn {
        padding: 12px 24px;
        font-size: 1.1rem;
        font-weight: bold;
        border: none;
        border-radius: 10px;
        cursor: pointer;
        transition: all 0.3s;
        display: flex;
        align-items: center;
        gap: 8px;
    }
    
    .spin-btn {
        background: linear-gradient(135deg, #ff416c, #ff4b2b);
        color: white;
        min-width: 120px;
    }
    
    .spin-btn:hover:not(:disabled) {
        transform: translateY(-3px);
        box-shadow: 0 10px 20px rgba(255, 65, 108, 0.4);
    }
    
    .spin-btn:disabled {
        opacity: 0.5;
        cursor: not-allowed;
    }
    
    .auto-btn {
        background: linear-gradient(135deg, #36d1dc, #5b86e5);
        color: white;
    }
    
    .auto-btn.active {
        background: linear-gradient(135deg, #ff4b2b, #ff416c);
    }
    
    .reset-btn {
        background: linear-gradient(135deg, #f46b45, #eea849);
        color: white;
    }
    
    .bet-btn {
        background: rgba(255, 215, 0, 0.2);
        color: #ffd700;
        border: 1px solid #ffd700;
        padding: 8px 16px;
    }
    
    /* Win Display */
    .win-display {
        background: linear-gradient(135deg, rgba(255, 215, 0, 0.1), transparent);
        border: 2px solid #ffd700;
        border-radius: 15px;
        padding: 20px;
        margin-top: 20px;
        animation: border-glow 2s infinite alternate;
    }
    
    .win-info {
        text-align: center;
        margin-bottom: 20px;
    }
    
    .win-amount {
        font-size: 3rem;
        font-weight: bold;
        color: #ffd700;
        text-shadow: 0 0 10px rgba(255, 215, 0, 0.5);
        margin-bottom: 10px;
    }
    
    .win-amount.win-animation {
        animation: win-pulse 0.5s infinite alternate;
    }
    
    .win-multiplier {
        font-size: 1.2rem;
        color: #ccc;
    }
    
    .win-lines-list {
        max-height: 200px;
        overflow-y: auto;
    }
    
    .win-line-item {
        background: rgba(255, 255, 255, 0.05);
        border-radius: 8px;
        padding: 10px;
        margin-bottom: 10px;
        border-left: 4px solid #ffd700;
    }
    
    .line-symbols {
        display: flex;
        gap: 10px;
        margin-bottom: 8px;
        justify-content: center;
    }
    
    .line-symbols .symbol {
        font-size: 1.5rem;
        width: 40px;
        height: 40px;
        display: flex;
        align-items: center;
        justify-content: center;
        background: rgba(255, 215, 0, 0.1);
        border-radius: 5px;
        border: 1px solid rgba(255, 215, 0, 0.3);
    }
    
    .line-info {
        display: flex;
        justify-content: space-between;
        font-size: 0.9rem;
    }
    
    .line-type {
        color: #ffd700;
        text-transform: uppercase;
        font-weight: bold;
    }
    
    .line-win {
        color: #4CAF50;
        font-weight: bold;
    }
    
    .no-wins {
        text-align: center;
        color: #777;
        font-style: italic;
        padding: 20px;
    }
    
    /* Win Lines Overlay */
    .win-lines-overlay {
        position: absolute;
        top: 0;
        left: 0;
        right: 0;
        bottom: 0;
        pointer-events: none;
        z-index: 1;
    }
    
    .win-line {
        position: absolute;
        background: transparent;
        transition: all 0.3s;
    }
    
    .win-line.active {
        background: rgba(255, 215, 0, 0.3);
        box-shadow: 0 0 20px rgba(255, 215, 0, 0.5);
    }
    
    /* Win line positions */
    .line-1 { top: 33%; height: 4px; width: 100%; }
    .line-2 { top: 50%; height: 4px; width: 100%; }
    .line-3 { top: 66%; height: 4px; width: 100%; }
    .line-4 { 
        top: 33%; left: 0; width: 100%; height: 34%;
        clip-path: polygon(0% 0%, 100% 0%, 75% 100%, 25% 100%);
    }
    .line-5 { 
        top: 33%; left: 0; width: 100%; height: 34%;
        clip-path: polygon(25% 0%, 75% 0%, 100% 100%, 0% 100%);
    }
    
    /* Animations */
    @keyframes shine {
        0% { transform: translateX(-100%) rotate(45deg); }
        100% { transform: translateX(100%) rotate(45deg); }
    }
    
    @keyframes spin-text {
        from { 
            opacity: 0.5;
            transform: translate(-50%, -50%) scale(0.9);
        }
        to { 
            opacity: 1;
            transform: translate(-50%, -50%) scale(1.1);
        }
    }
    
    @keyframes reel-spin {
        from { transform: translateY(0); }
        to { transform: translateY(-100px); }
    }
    
    @keyframes reel-stop {
        0% { transform: translateY(-10px); }
        50% { transform: translateY(5px); }
        100% { transform: translateY(0); }
    }
    
    @keyframes win-symbol {
        from {
            box-shadow: 
                inset 0 0 20px rgba(255, 215, 0, 0.5),
                0 0 30px rgba(255, 215, 0, 0.7);
            transform: scale(1.1);
        }
        to {
            box-shadow: 
                inset 0 0 30px rgba(255, 215, 0, 0.8),
                0 0 50px rgba(255, 215, 0, 1);
            transform: scale(1.2);
        }
    }
    
    @keyframes win-pulse {
        from {
            transform: scale(1);
            text-shadow: 0 0 10px rgba(255, 215, 0, 0.5);
        }
        to {
            transform: scale(1.1);
            text-shadow: 
                0 0 20px rgba(255, 215, 0, 0.8),
                0 0 30px rgba(255, 215, 0, 1);
        }
    }
    
    @keyframes border-glow {
        from { box-shadow: 0 0 10px rgba(255, 215, 0, 0.3); }
        to { box-shadow: 0 0 30px rgba(255, 215, 0, 0.7); }
    }
    
    /* Win Animation for Machine */
    .slot-machine.win-animation {
        animation: machine-win 2s;
    }
    
    @keyframes machine-win {
        0% { border-color: #ffd700; }
        25% { border-color: #ff416c; }
        50% { border-color: #36d1dc; }
        75% { border-color: #4CAF50; }
        100% { border-color: #ffd700; }
    }
    `;
    
    const styleSheet = document.createElement('style');
    styleSheet.textContent = slotStyles;
    document.head.appendChild(styleSheet);
});

if (typeof module !== 'undefined' && module.exports) {
    module.exports = SlotMachine;
} else {
    window.SlotMachine = SlotMachine;
}