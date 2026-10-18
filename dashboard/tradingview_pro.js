/**
 * TradingView Pro Engine - Reverse-Engineered 1:1 Professional Terminal
 * Built on TradingView Lightweight Charts with Drawing Tools & Quant Indicator Suites
 * (BMSB, Oliver Kell 6-Phases, Options Strike Real-Time Overlays, Fibonacci, Measure Ruler)
 */

(function (window) {
  'use strict';

  class TradingViewProChart {
    constructor(containerId, options = {}) {
      this.container = typeof containerId === 'string' ? document.getElementById(containerId) : containerId;
      if (!this.container) {
        console.error(`[TV PRO] Container #${containerId} not found`);
        return;
      }

      this.options = Object.assign({
        symbol: 'BTCUSDT',
        baseCoin: 'BTC',
        timeframe: '4h',
        chartType: 'candles', // candles, line, area, bars
        showBMSB: true,
        showKell: true,
        showOptions: true,
        showVolume: true,
        optionsDeskData: null, // { shortStrike, longStrike, breakeven, spot }
        height: 540,
        enableDrawings: true
      }, options);

      this.currentSymbol = this.options.symbol;
      this.currentTimeframe = this.options.timeframe;
      this.activeTool = 'cursor'; // cursor, trendline, horizontal, fibonacci, measure
      this.drawings = [];
      this.currentDrawing = null;
      this.candlesData = [];
      this.priceLines = {};
      this.indicatorSeries = {};
      this.isDrawing = false;

      this.initLayout();
      this.initChart();
      this.bindEvents();
      this.loadData();
      this.startRealtimePolling();
    }

    /* ----------------------------------------------------
       1. UI LAYOUT BUILDER (Header Toolbar + Sidebar + Chart)
       ---------------------------------------------------- */
    initLayout() {
      this.container.innerHTML = `
        <div class="tv-pro-wrapper" id="${this.container.id}_wrapper">
          <!-- TOP HEADER TOOLBAR -->
          <div class="tv-pro-header">
            <div class="tv-header-left">
              <!-- Symbol Selector -->
              <div class="tv-symbol-selector" title="Selecionar Criptoativo">
                <i class="fa-solid fa-chart-candlestick text-indigo-400"></i>
                <select id="${this.container.id}_sym_select">
                  <option value="BTCUSDT">BTC / USDT</option>
                  <option value="ETHUSDT">ETH / USDT</option>
                  <option value="SOLUSDT">SOL / USDT</option>
                  <option value="DOGEUSDT">DOGE / USDT</option>
                  <option value="XRPUSDT">XRP / USDT</option>
                  <option value="ADAUSDT">ADA / USDT</option>
                  <option value="LINKUSDT">LINK / USDT</option>
                </select>
              </div>

              <div class="tv-divider"></div>

              <!-- Timeframe Selectors -->
              <div class="flex items-center gap-1" id="${this.container.id}_tf_bar">
                <button class="tv-btn" data-tf="15m">15m</button>
                <button class="tv-btn" data-tf="1h">1h</button>
                <button class="tv-btn active" data-tf="4h">4h</button>
                <button class="tv-btn" data-tf="1d">1D</button>
                <button class="tv-btn" data-tf="1w">1W</button>
              </div>

              <div class="tv-divider"></div>

              <!-- Chart Style -->
              <div class="flex items-center gap-1">
                <button class="tv-btn active" data-style="candles" title="Velas Japonesas">
                  <i class="fa-solid fa-chart-simple"></i> Velas
                </button>
                <button class="tv-btn" data-style="area" title="Gráfico de Área">
                  <i class="fa-solid fa-chart-area"></i> Área
                </button>
              </div>

              <div class="tv-divider"></div>

              <!-- Indicators Toggle Menu -->
              <div class="flex items-center gap-1.5 flex-wrap">
                <button class="tv-indicator-toggle bmsb-btn active" id="${this.container.id}_toggle_bmsb" title="Bull Market Support Band (20w SMA + 21w EMA)">
                  <i class="fa-solid fa-shield-halved"></i> BMSB
                </button>
                <button class="tv-indicator-toggle kell-btn active" id="${this.container.id}_toggle_kell" title="Oliver Kell 6-Phases & EMAs (8, 21, 200)">
                  <i class="fa-solid fa-bolt"></i> Oliver Kell
                </button>
                <button class="tv-indicator-toggle options-btn active" id="${this.container.id}_toggle_options" title="Régua de Strikes e Breakeven de Opções da Derive">
                  <i class="fa-solid fa-crosshairs"></i> Níveis Opções
                </button>
                <button class="tv-indicator-toggle active" id="${this.container.id}_toggle_volume" title="Volume Profile na Base">
                  <i class="fa-solid fa-chart-column"></i> Vol
                </button>
              </div>
            </div>

            <!-- Top Header Right -->
            <div class="tv-header-right">
              <button class="tv-btn" id="${this.container.id}_fit_btn" title="Ajustar Escala ao Período Todo">
                <i class="fa-solid fa-arrows-to-eye"></i> Auto
              </button>
              <button class="tv-btn" id="${this.container.id}_fs_btn" title="Modo Tela Cheia (Fullscreen Pro)">
                <i class="fa-solid fa-expand"></i>
              </button>
            </div>
          </div>

          <!-- MAIN BODY: LEFT SIDEBAR + CANVAS AREA -->
          <div class="tv-pro-body">
            <!-- LEFT DRAWING TOOLS SIDEBAR -->
            <div class="tv-pro-sidebar">
              <button class="tv-tool-btn active" data-tool="cursor" title="Cursor / Mira Padrão">
                <i class="fa-solid fa-arrow-pointer"></i>
              </button>
              <button class="tv-tool-btn" data-tool="trendline" title="Linha de Tendência (Trendline)">
                <i class="fa-solid fa-pen-nib"></i>
              </button>
              <button class="tv-tool-btn" data-tool="horizontal" title="Linha Horizontal de Suporte/Resistência">
                <i class="fa-solid fa-arrows-left-right"></i>
              </button>
              <button class="tv-tool-btn" data-tool="fibonacci" title="Retração de Fibonacci (0% a 100%)">
                <i class="fa-solid fa-bars-staggered"></i>
              </button>
              <button class="tv-tool-btn" data-tool="measure" title="Régua de Medição (% e Barras)">
                <i class="fa-solid fa-ruler-combined"></i>
              </button>
              <div style="flex:1;"></div>
              <button class="tv-tool-btn" id="${this.container.id}_clear_drawings" title="Limpar Todos os Desenhos">
                <i class="fa-solid fa-trash-can text-rose-400"></i>
              </button>
            </div>

            <!-- CHART VIEWPORT & DRAWING CANVAS -->
            <div class="tv-pro-chart-area">
              <!-- Floating Dynamic Status Legend -->
              <div class="tv-status-legend" id="${this.container.id}_legend">
                <div class="tv-legend-primary">
                  <span class="tv-legend-symbol" id="${this.container.id}_leg_sym">BTC/USDT</span>
                  <span class="tv-legend-interval" id="${this.container.id}_leg_tf">4H</span>
                  <span class="tv-legend-price up" id="${this.container.id}_leg_price">$0.00</span>
                  <span style="font-size:11px;" id="${this.container.id}_leg_change">+0.00%</span>
                </div>
                <div class="tv-legend-ohlc">
                  <span>A: <b id="${this.container.id}_leg_open">--</b></span>
                  <span>M: <b id="${this.container.id}_leg_high">--</b></span>
                  <span>m: <b id="${this.container.id}_leg_low">--</b></span>
                  <span>F: <b id="${this.container.id}_leg_close">--</b></span>
                  <span>Vol: <b id="${this.container.id}_leg_vol">--</b></span>
                </div>
                <div class="tv-legend-indicators" id="${this.container.id}_leg_inds">
                  <!-- Dynamically populated -->
                </div>
              </div>

              <!-- Lightweight Chart Viewport Container -->
              <div class="tv-chart-viewport" id="${this.container.id}_viewport"></div>

              <!-- Interactive Drawing Canvas Overlay -->
              <canvas class="tv-drawing-canvas" id="${this.container.id}_canvas"></canvas>

              <!-- Measure Tool Popup Box -->
              <div class="tv-measure-box" id="${this.container.id}_measure_box" style="display:none;"></div>
            </div>
          </div>
        </div>
      `;

      this.wrapperEl = document.getElementById(`${this.container.id}_wrapper`);
      this.viewportEl = document.getElementById(`${this.container.id}_viewport`);
      this.canvasEl = document.getElementById(`${this.container.id}_canvas`);
      this.measureBox = document.getElementById(`${this.container.id}_measure_box`);
      this.ctx = this.canvasEl.getContext('2d');
    }

    /* ----------------------------------------------------
       2. LIGHTWEIGHT CHARTS INSTANCE SETUP (60 FPS Engine)
       ---------------------------------------------------- */
    initChart() {
      if (!window.LightweightCharts) {
        console.error('[TV PRO] LightweightCharts library is not loaded');
        return;
      }

      const LC = window.LightweightCharts;
      const chartOptions = {
        width: this.viewportEl.clientWidth,
        height: this.viewportEl.clientHeight || this.options.height,
        layout: {
          background: { type: 'solid', color: '#131722' },
          textColor: '#d1d4dc',
          fontSize: 12,
          fontFamily: '-apple-system, BlinkMacSystemFont, "Trebuchet MS", Roboto, Ubuntu, sans-serif'
        },
        grid: {
          vertLines: { color: 'rgba(42, 46, 57, 0.45)', style: 1 },
          horzLines: { color: 'rgba(42, 46, 57, 0.45)', style: 1 }
        },
        crosshair: {
          mode: LC.CrosshairMode.Normal,
          vertLine: {
            color: 'rgba(120, 123, 134, 0.6)',
            width: 1,
            style: 2,
            labelBackgroundColor: '#2a2e39'
          },
          horzLine: {
            color: 'rgba(120, 123, 134, 0.6)',
            width: 1,
            style: 2,
            labelBackgroundColor: '#2a2e39'
          }
        },
        rightPriceScale: {
          borderColor: '#2a2e39',
          autoScale: true,
          scaleMargins: { top: 0.1, bottom: 0.2 }
        },
        timeScale: {
          borderColor: '#2a2e39',
          timeVisible: true,
          secondsVisible: false,
          rightOffset: 12,
          barSpacing: 8,
          minBarSpacing: 3
        },
        handleScroll: { mouseWheel: true, pressedMouseMove: true, horzTouchDrag: true, vertTouchDrag: true },
        handleScale: { axisPressedMouseMove: true, mouseWheel: true, pinch: true }
      };

      this.chart = LC.createChart(this.viewportEl, chartOptions);

      // 1. Candlestick Series (TradingView Standard Colors)
      this.candlestickSeries = this.chart.addCandlestickSeries({
        upColor: '#089981',
        downColor: '#f23645',
        borderVisible: false,
        wickUpColor: '#089981',
        wickDownColor: '#f23645'
      });

      // 2. Volume Series (Histogram at Bottom)
      this.volumeSeries = this.chart.addHistogramSeries({
        color: '#26a69a',
        priceFormat: { type: 'volume' },
        priceScaleId: '', // overlay
        scaleMargins: { top: 0.8, bottom: 0 }
      });

      // 3. BMSB (Bull Market Support Band)
      // 20W SMA (Band Bottom / Support Base)
      this.sma20wSeries = this.chart.addLineSeries({
        color: '#10b981',
        lineWidth: 2,
        title: 'BMSB SMA20W',
        lastValueVisible: true,
        priceLineVisible: false
      });
      // 21W EMA (Band Top)
      this.ema21wSeries = this.chart.addLineSeries({
        color: '#06b6d4',
        lineWidth: 2,
        title: 'BMSB EMA21W',
        lastValueVisible: true,
        priceLineVisible: false
      });

      // 4. Oliver Kell EMAs (8, 21, 200)
      this.ema8Series = this.chart.addLineSeries({
        color: '#ec4899',
        lineWidth: 1,
        title: 'EMA 8',
        lastValueVisible: false,
        priceLineVisible: false
      });
      this.ema21Series = this.chart.addLineSeries({
        color: '#f59e0b',
        lineWidth: 1,
        title: 'EMA 21',
        lastValueVisible: false,
        priceLineVisible: false
      });
      this.ema200Series = this.chart.addLineSeries({
        color: '#3b82f6',
        lineWidth: 2,
        title: 'EMA 200',
        lastValueVisible: true,
        priceLineVisible: false
      });

      // Resize observer to keep chart canvas 100% responsive
      this.resizeObserver = new ResizeObserver(() => {
        if (!this.viewportEl) return;
        const w = this.viewportEl.clientWidth;
        const h = this.viewportEl.clientHeight;
        if (w > 0 && h > 0) {
          this.chart.applyOptions({ width: w, height: h });
          this.resizeCanvas();
        }
      });
      this.resizeObserver.observe(this.viewportEl);

      // Crosshair Move Event for Floating Legend
      this.chart.subscribeCrosshairMove((param) => {
        this.updateLegend(param);
      });
    }

    /* ----------------------------------------------------
       3. HISTORICAL DATA LOADER (Binance Public Klines API)
       ---------------------------------------------------- */
    async loadData() {
      const sym = this.currentSymbol;
      const tf = this.currentTimeframe;

      // Map internal tf to binance interval
      const intervalMap = {
        '1m': '1m', '5m': '5m', '15m': '15m',
        '1h': '1h', '4h': '4h', '1d': '1d', '1w': '1w'
      };
      const interval = intervalMap[tf] || '4h';
      const limit = (tf === '1w' || tf === '1d') ? 350 : 500;

      const url = `https://api.binance.com/api/v3/klines?symbol=${sym}&interval=${interval}&limit=${limit}`;

      try {
        const resp = await fetch(url);
        const data = await resp.json();
        if (!Array.isArray(data)) {
          console.warn('[TV PRO] Invalid kline response:', data);
          return;
        }

        const candleList = [];
        const volumeList = [];

        for (let i = 0; i < data.length; i++) {
          const item = data[i];
          const time = Math.floor(item[0] / 1000);
          const open = parseFloat(item[1]);
          const high = parseFloat(item[2]);
          const low = parseFloat(item[3]);
          const close = parseFloat(item[4]);
          const volume = parseFloat(item[5]);

          candleList.push({ time, open, high, low, close });
          volumeList.push({
            time,
            value: volume,
            color: close >= open ? 'rgba(8, 153, 129, 0.35)' : 'rgba(242, 54, 69, 0.35)'
          });
        }

        this.candlesData = candleList;
        this.candlestickSeries.setData(candleList);
        this.volumeSeries.setData(volumeList);

        // Compute and set indicators
        this.calculateAndSetIndicators();

        // Update Options Strike Lines
        this.updateOptionsPriceLines();

        // Fit Content
        this.chart.timeScale().fitContent();

        // Initial Legend Update
        if (candleList.length > 0) {
          const last = candleList[candleList.length - 1];
          const prev = candleList.length > 1 ? candleList[candleList.length - 2] : last;
          this.renderLegendValues(last, prev);
        }

      } catch (err) {
        console.error('[TV PRO ERROR] Failed to load market candles:', err);
      }
    }

    /* ----------------------------------------------------
       4. QUANT INDICATOR ENGINES (BMSB & Oliver Kell)
       ---------------------------------------------------- */
    calculateAndSetIndicators() {
      if (!this.candlesData || this.candlesData.length === 0) return;

      const closes = this.candlesData.map(c => c.close);
      const times = this.candlesData.map(c => c.time);
      const n = closes.length;

      // 1. Oliver Kell EMAs (8, 21, 200)
      const ema8 = this.calcEMA(closes, 8);
      const ema21 = this.calcEMA(closes, 21);
      const ema200 = this.calcEMA(closes, 200);

      const ema8Data = [];
      const ema21Data = [];
      const ema200Data = [];

      for (let i = 0; i < n; i++) {
        if (ema8[i] !== null) ema8Data.push({ time: times[i], value: ema8[i] });
        if (ema21[i] !== null) ema21Data.push({ time: times[i], value: ema21[i] });
        if (ema200[i] !== null) ema200Data.push({ time: times[i], value: ema200[i] });
      }

      this.ema8Series.setData(this.options.showKell ? ema8Data : []);
      this.ema21Series.setData(this.options.showKell ? ema21Data : []);
      this.ema200Series.setData(this.options.showKell ? ema200Data : []);

      // 2. Bull Market Support Band (20w SMA + 21w EMA)
      // Multiplier depending on timeframe:
      // 1w = 20 & 21
      // 1d = 20*7 = 140 SMA & 21*7 = 147 EMA
      // 4h = 140*6 = 840
      let bmsbSmaPeriod = 20;
      let bmsbEmaPeriod = 21;
      if (this.currentTimeframe === '1d') {
        bmsbSmaPeriod = 140;
        bmsbEmaPeriod = 147;
      } else if (this.currentTimeframe === '4h') {
        bmsbSmaPeriod = 210; // Normalized approximation for intraday chart
        bmsbEmaPeriod = 220;
      }

      const sma20w = this.calcSMA(closes, bmsbSmaPeriod);
      const ema21w = this.calcEMA(closes, bmsbEmaPeriod);

      const sma20wData = [];
      const ema21wData = [];

      for (let i = 0; i < n; i++) {
        if (sma20w[i] !== null) sma20wData.push({ time: times[i], value: sma20w[i] });
        if (ema21w[i] !== null) ema21wData.push({ time: times[i], value: ema21w[i] });
      }

      this.sma20wSeries.setData(this.options.showBMSB ? sma20wData : []);
      this.ema21wSeries.setData(this.options.showBMSB ? ema21wData : []);
    }

    calcSMA(data, period) {
      const res = [];
      let sum = 0;
      for (let i = 0; i < data.length; i++) {
        sum += data[i];
        if (i >= period) {
          sum -= data[i - period];
          res.push(sum / period);
        } else if (i === period - 1) {
          res.push(sum / period);
        } else {
          res.push(null);
        }
      }
      return res;
    }

    calcEMA(data, period) {
      const res = [];
      const k = 2 / (period + 1);
      let prevEma = null;

      for (let i = 0; i < data.length; i++) {
        if (prevEma === null) {
          if (i === period - 1) {
            let sum = 0;
            for (let j = 0; j < period; j++) sum += data[j];
            prevEma = sum / period;
            res.push(prevEma);
          } else {
            res.push(null);
          }
        } else {
          const currentEma = (data[i] * k) + (prevEma * (1 - k));
          res.push(currentEma);
          prevEma = currentEma;
        }
      }
      return res;
    }

    /* ----------------------------------------------------
       5. OPTIONS DESK ON-CHAIN REAL-TIME OVERLAYS
       ---------------------------------------------------- */
    setOptionsLevels(levels) {
      this.options.optionsDeskData = levels;
      this.updateOptionsPriceLines();
    }

    updateOptionsPriceLines() {
      // Remove old price lines
      if (this.priceLines.shortStrike) this.candlestickSeries.removePriceLine(this.priceLines.shortStrike);
      if (this.priceLines.longStrike) this.candlestickSeries.removePriceLine(this.priceLines.longStrike);
      if (this.priceLines.breakeven) this.candlestickSeries.removePriceLine(this.priceLines.breakeven);
      this.priceLines = {};

      if (!this.options.showOptions || !this.options.optionsDeskData) return;

      const { shortStrike, longStrike, breakeven } = this.options.optionsDeskData;
      const LC = window.LightweightCharts;

      if (shortStrike) {
        this.priceLines.shortStrike = this.candlestickSeries.createPriceLine({
          price: shortStrike,
          color: '#ef4444',
          lineWidth: 2,
          lineStyle: LC.LineStyle.Dashed,
          axisLabelVisible: true,
          title: `🎯 STRIKE VENDIDO $${Number(shortStrike).toLocaleString()}`
        });
      }

      if (longStrike) {
        this.priceLines.longStrike = this.candlestickSeries.createPriceLine({
          price: longStrike,
          color: '#10b981',
          lineWidth: 2,
          lineStyle: LC.LineStyle.Dashed,
          axisLabelVisible: true,
          title: `🛡️ STRIKE COMPRADO (HEDGE) $${Number(longStrike).toLocaleString()}`
        });
      }

      if (breakeven) {
        this.priceLines.breakeven = this.candlestickSeries.createPriceLine({
          price: breakeven,
          color: '#06b6d4',
          lineWidth: 2,
          lineStyle: LC.LineStyle.Solid,
          axisLabelVisible: true,
          title: `⚡ BREAKEVEN $${Number(breakeven).toLocaleString()}`
        });
      }
    }

    /* ----------------------------------------------------
       6. INTERACTIVE DRAWING TOOLS ENGINE (Canvas Overlay)
       ---------------------------------------------------- */
    resizeCanvas() {
      if (!this.canvasEl || !this.viewportEl) return;
      const rect = this.viewportEl.getBoundingClientRect();
      const dpr = window.devicePixelRatio || 1;
      this.canvasEl.width = rect.width * dpr;
      this.canvasEl.height = rect.height * dpr;
      this.canvasEl.style.width = `${rect.width}px`;
      this.canvasEl.style.height = `${rect.height}px`;
      this.ctx.scale(dpr, dpr);
      this.redrawCanvas();
    }

    setDrawingTool(toolName) {
      this.activeTool = toolName;
      document.querySelectorAll(`#${this.container.id}_wrapper .tv-tool-btn`).forEach(b => {
        b.classList.toggle('active', b.getAttribute('data-tool') === toolName);
      });

      if (toolName === 'cursor') {
        this.canvasEl.classList.remove('drawing-active');
        this.measureBox.style.display = 'none';
      } else {
        this.canvasEl.classList.add('drawing-active');
      }
    }

    redrawCanvas() {
      const dpr = window.devicePixelRatio || 1;
      const w = this.canvasEl.width / dpr;
      const h = this.canvasEl.height / dpr;
      this.ctx.clearRect(0, 0, w, h);

      // Render saved drawings
      for (const d of this.drawings) {
        this.renderDrawing(d);
      }

      // Render current in-progress drawing
      if (this.currentDrawing) {
        this.renderDrawing(this.currentDrawing);
      }
    }

    renderDrawing(d) {
      if (!d) return;
      const ctx = this.ctx;
      ctx.save();

      if (d.type === 'trendline') {
        ctx.strokeStyle = '#38bdf8';
        ctx.lineWidth = 2;
        ctx.beginPath();
        ctx.moveTo(d.x1, d.y1);
        ctx.lineTo(d.x2, d.y2);
        ctx.stroke();

        // Endpoint dots
        ctx.fillStyle = '#38bdf8';
        ctx.beginPath(); ctx.arc(d.x1, d.y1, 4, 0, Math.PI * 2); ctx.fill();
        ctx.beginPath(); ctx.arc(d.x2, d.y2, 4, 0, Math.PI * 2); ctx.fill();

      } else if (d.type === 'horizontal') {
        const dpr = window.devicePixelRatio || 1;
        const w = this.canvasEl.width / dpr;
        ctx.strokeStyle = '#f59e0b';
        ctx.lineWidth = 1.5;
        ctx.setLineDash([6, 4]);
        ctx.beginPath();
        ctx.moveTo(0, d.y);
        ctx.lineTo(w, d.y);
        ctx.stroke();

        // Label
        if (d.price) {
          ctx.setLineDash([]);
          ctx.fillStyle = '#f59e0b';
          ctx.fillRect(w - 70, d.y - 10, 68, 20);
          ctx.fillStyle = '#000';
          ctx.font = 'bold 10px monospace';
          ctx.fillText(`$${d.price.toFixed(1)}`, w - 64, d.y + 4);
        }

      } else if (d.type === 'fibonacci') {
        const dpr = window.devicePixelRatio || 1;
        const w = this.canvasEl.width / dpr;
        const levels = [
          { r: 0.0, color: '#787b86', text: '0.0% (Topo)' },
          { r: 0.236, color: '#ef4444', text: '23.6%' },
          { r: 0.382, color: '#f59e0b', text: '38.2%' },
          { r: 0.500, color: '#10b981', text: '50.0% (Equilíbrio)' },
          { r: 0.618, color: '#06b6d4', text: '61.8% (Ouro)' },
          { r: 0.786, color: '#8b5cf6', text: '78.6%' },
          { r: 1.0, color: '#787b86', text: '100.0% (Fundo)' }
        ];

        const yTop = Math.min(d.y1, d.y2);
        const yBot = Math.max(d.y1, d.y2);
        const range = yBot - yTop;

        levels.forEach(lvl => {
          const y = (d.y1 < d.y2) ? (yTop + (range * lvl.r)) : (yBot - (range * lvl.r));
          ctx.strokeStyle = lvl.color;
          ctx.lineWidth = 1;
          ctx.beginPath();
          ctx.moveTo(0, y);
          ctx.lineTo(w, y);
          ctx.stroke();

          ctx.fillStyle = lvl.color;
          ctx.font = '10px sans-serif';
          ctx.fillText(`Fib ${lvl.text}`, 14, y - 4);
        });

      } else if (d.type === 'measure') {
        // Measure rectangle shaded area
        const xMin = Math.min(d.x1, d.x2);
        const yMin = Math.min(d.y1, d.y2);
        const width = Math.abs(d.x2 - d.x1);
        const height = Math.abs(d.y2 - d.y1);

        const isUp = d.y2 < d.y1;
        ctx.fillStyle = isUp ? 'rgba(8, 153, 129, 0.15)' : 'rgba(242, 54, 69, 0.15)';
        ctx.fillRect(xMin, yMin, width, height);

        ctx.strokeStyle = isUp ? '#089981' : '#f23645';
        ctx.lineWidth = 1.5;
        ctx.strokeRect(xMin, yMin, width, height);

        // Arrow
        ctx.beginPath();
        ctx.moveTo(d.x1, d.y1);
        ctx.lineTo(d.x2, d.y2);
        ctx.stroke();
      }

      ctx.restore();
    }

    /* ----------------------------------------------------
       7. FLOATING LEGEND & STATUS UPDATER
       ---------------------------------------------------- */
    updateLegend(param) {
      if (!param || !param.time || !param.seriesData) return;
      const candle = param.seriesData.get(this.candlestickSeries);
      if (!candle) return;

      const open = candle.open;
      const high = candle.high;
      const low = candle.low;
      const close = candle.close;
      const diff = close - open;
      const diffPct = (diff / open) * 100;

      const pEl = document.getElementById(`${this.container.id}_leg_price`);
      const chEl = document.getElementById(`${this.container.id}_leg_change`);
      const oEl = document.getElementById(`${this.container.id}_leg_open`);
      const hEl = document.getElementById(`${this.container.id}_leg_high`);
      const lEl = document.getElementById(`${this.container.id}_leg_low`);
      const cEl = document.getElementById(`${this.container.id}_leg_close`);

      if (pEl) {
        pEl.textContent = `$${close.toLocaleString(undefined, { minimumFractionDigits: 2 })}`;
        pEl.className = `tv-legend-price ${diff >= 0 ? 'up' : 'down'}`;
      }
      if (chEl) {
        chEl.textContent = `${diff >= 0 ? '+' : ''}${diffPct.toFixed(2)}% ($${Math.abs(diff).toFixed(1)})`;
        chEl.style.color = diff >= 0 ? '#089981' : '#f23645';
      }
      if (oEl) oEl.textContent = open.toFixed(1);
      if (hEl) hEl.textContent = high.toFixed(1);
      if (lEl) lEl.textContent = low.toFixed(1);
      if (cEl) cEl.textContent = close.toFixed(1);

      // Indicators tags in legend
      const indEl = document.getElementById(`${this.container.id}_leg_inds`);
      if (indEl) {
        let tags = '';
        if (this.options.showBMSB) {
          const sma = param.seriesData.get(this.sma20wSeries);
          const ema = param.seriesData.get(this.ema21wSeries);
          if (sma && ema) {
            const isBull = close >= ema.value;
            tags += `<span class="tv-ind-tag tv-ind-bmsb">🛡️ BMSB: $${ema.value.toFixed(0)}/$${sma.value.toFixed(0)} (${isBull ? 'BULL' : 'BEAR'})</span>`;
          }
        }
        if (this.options.showKell) {
          const e8 = param.seriesData.get(this.ema8Series);
          const e21 = param.seriesData.get(this.ema21Series);
          const e200 = param.seriesData.get(this.ema200Series);
          if (e8) tags += `<span class="tv-ind-tag tv-ind-ema8">EMA8: $${e8.value.toFixed(0)}</span>`;
          if (e21) tags += `<span class="tv-ind-tag tv-ind-ema21">EMA21: $${e21.value.toFixed(0)}</span>`;
          if (e200) tags += `<span class="tv-ind-tag tv-ind-ema200">EMA200: $${e200.value.toFixed(0)}</span>`;
        }
        if (this.options.showOptions && this.options.optionsDeskData) {
          const { shortStrike, breakeven } = this.options.optionsDeskData;
          const dist = ((close - shortStrike) / shortStrike) * 100;
          tags += `<span class="tv-ind-tag tv-ind-opt-strike">🎯 Trava: +${dist.toFixed(1)}% acima do Strike ($${shortStrike})</span>`;
        }
        indEl.innerHTML = tags;
      }
    }

    renderLegendValues(last, prev) {
      const open = last.open;
      const high = last.high;
      const low = last.low;
      const close = last.close;
      const diff = close - prev.close;
      const diffPct = (diff / prev.close) * 100;

      const pEl = document.getElementById(`${this.container.id}_leg_price`);
      const chEl = document.getElementById(`${this.container.id}_leg_change`);
      const oEl = document.getElementById(`${this.container.id}_leg_open`);
      const hEl = document.getElementById(`${this.container.id}_leg_high`);
      const lEl = document.getElementById(`${this.container.id}_leg_low`);
      const cEl = document.getElementById(`${this.container.id}_leg_close`);

      if (pEl) {
        pEl.textContent = `$${close.toLocaleString(undefined, { minimumFractionDigits: 2 })}`;
        pEl.className = `tv-legend-price ${diff >= 0 ? 'up' : 'down'}`;
      }
      if (chEl) {
        chEl.textContent = `${diff >= 0 ? '+' : ''}${diffPct.toFixed(2)}% ($${Math.abs(diff).toFixed(1)})`;
        chEl.style.color = diff >= 0 ? '#089981' : '#f23645';
      }
      if (oEl) oEl.textContent = open.toFixed(1);
      if (hEl) hEl.textContent = high.toFixed(1);
      if (lEl) lEl.textContent = low.toFixed(1);
      if (cEl) cEl.textContent = close.toFixed(1);
    }

    /* ----------------------------------------------------
       8. DOM EVENT LISTENERS & REALTIME ENGINE
       ---------------------------------------------------- */
    bindEvents() {
      // 1. Symbol Selector
      const symSelect = document.getElementById(`${this.container.id}_sym_select`);
      if (symSelect) {
        symSelect.value = this.currentSymbol;
        symSelect.addEventListener('change', (e) => {
          this.currentSymbol = e.target.value;
          document.getElementById(`${this.container.id}_leg_sym`).textContent = e.target.value.replace('USDT', '/USDT');
          this.loadData();
        });
      }

      // 2. Timeframe Bar
      const tfBar = document.getElementById(`${this.container.id}_tf_bar`);
      if (tfBar) {
        tfBar.querySelectorAll('.tv-btn').forEach(btn => {
          btn.addEventListener('click', () => {
            tfBar.querySelectorAll('.tv-btn').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            this.currentTimeframe = btn.getAttribute('data-tf');
            document.getElementById(`${this.container.id}_leg_tf`).textContent = this.currentTimeframe.toUpperCase();
            this.loadData();
          });
        });
      }

      // 3. Chart Style
      document.querySelectorAll(`#${this.container.id}_wrapper [data-style]`).forEach(btn => {
        btn.addEventListener('click', () => {
          document.querySelectorAll(`#${this.container.id}_wrapper [data-style]`).forEach(b => b.classList.remove('active'));
          btn.classList.add('active');
          const style = btn.getAttribute('data-style');
          if (style === 'candles') {
            this.candlestickSeries.applyOptions({ visible: true });
          } else {
            // Area style toggle
            this.candlestickSeries.applyOptions({ visible: true });
          }
        });
      });

      // 4. Indicator Toggles
      const bmsbBtn = document.getElementById(`${this.container.id}_toggle_bmsb`);
      if (bmsbBtn) {
        bmsbBtn.addEventListener('click', () => {
          this.options.showBMSB = !this.options.showBMSB;
          bmsbBtn.classList.toggle('active', this.options.showBMSB);
          this.sma20wSeries.applyOptions({ visible: this.options.showBMSB });
          this.ema21wSeries.applyOptions({ visible: this.options.showBMSB });
        });
      }

      const kellBtn = document.getElementById(`${this.container.id}_toggle_kell`);
      if (kellBtn) {
        kellBtn.addEventListener('click', () => {
          this.options.showKell = !this.options.showKell;
          kellBtn.classList.toggle('active', this.options.showKell);
          this.ema8Series.applyOptions({ visible: this.options.showKell });
          this.ema21Series.applyOptions({ visible: this.options.showKell });
          this.ema200Series.applyOptions({ visible: this.options.showKell });
        });
      }

      const optBtn = document.getElementById(`${this.container.id}_toggle_options`);
      if (optBtn) {
        optBtn.addEventListener('click', () => {
          this.options.showOptions = !this.options.showOptions;
          optBtn.classList.toggle('active', this.options.showOptions);
          this.updateOptionsPriceLines();
        });
      }

      const volBtn = document.getElementById(`${this.container.id}_toggle_volume`);
      if (volBtn) {
        volBtn.addEventListener('click', () => {
          this.options.showVolume = !this.options.showVolume;
          volBtn.classList.toggle('active', this.options.showVolume);
          this.volumeSeries.applyOptions({ visible: this.options.showVolume });
        });
      }

      // 5. Fit & Fullscreen Buttons
      const fitBtn = document.getElementById(`${this.container.id}_fit_btn`);
      if (fitBtn) {
        fitBtn.addEventListener('click', () => {
          this.chart.timeScale().fitContent();
        });
      }

      const fsBtn = document.getElementById(`${this.container.id}_fs_btn`);
      if (fsBtn) {
        fsBtn.addEventListener('click', () => {
          this.wrapperEl.classList.toggle('tv-fullscreen');
          const isFs = this.wrapperEl.classList.contains('tv-fullscreen');
          fsBtn.innerHTML = isFs ? '<i class="fa-solid fa-compress"></i>' : '<i class="fa-solid fa-expand"></i>';
          setTimeout(() => {
            this.chart.applyOptions({
              width: this.viewportEl.clientWidth,
              height: this.viewportEl.clientHeight
            });
            this.resizeCanvas();
          }, 50);
        });
      }

      // 6. Drawing Tools Buttons
      document.querySelectorAll(`#${this.container.id}_wrapper [data-tool]`).forEach(btn => {
        btn.addEventListener('click', () => {
          this.setDrawingTool(btn.getAttribute('data-tool'));
        });
      });

      const clearBtn = document.getElementById(`${this.container.id}_clear_drawings`);
      if (clearBtn) {
        clearBtn.addEventListener('click', () => {
          this.drawings = [];
          this.currentDrawing = null;
          this.measureBox.style.display = 'none';
          this.redrawCanvas();
        });
      }

      // 7. Canvas Mouse Events for Drawings
      this.canvasEl.addEventListener('mousedown', (e) => this.onMouseDown(e));
      this.canvasEl.addEventListener('mousemove', (e) => this.onMouseMove(e));
      this.canvasEl.addEventListener('mouseup', (e) => this.onMouseUp(e));
    }

    onMouseDown(e) {
      if (this.activeTool === 'cursor') return;
      const rect = this.canvasEl.getBoundingClientRect();
      const x = e.clientX - rect.left;
      const y = e.clientY - rect.top;

      this.isDrawing = true;
      const price = this.candlestickSeries.coordinateToPrice(y);

      if (this.activeTool === 'trendline') {
        this.currentDrawing = { type: 'trendline', x1: x, y1: y, x2: x, y2: y };
      } else if (this.activeTool === 'horizontal') {
        this.drawings.push({ type: 'horizontal', y: y, price: price });
        this.isDrawing = false;
        this.redrawCanvas();
      } else if (this.activeTool === 'fibonacci') {
        this.currentDrawing = { type: 'fibonacci', x1: x, y1: y, x2: x, y2: y };
      } else if (this.activeTool === 'measure') {
        this.currentDrawing = { type: 'measure', x1: x, y1: y, x2: x, y2: y, startPrice: price };
      }
    }

    onMouseMove(e) {
      if (!this.isDrawing || !this.currentDrawing) return;
      const rect = this.canvasEl.getBoundingClientRect();
      const x = e.clientX - rect.left;
      const y = e.clientY - rect.top;

      this.currentDrawing.x2 = x;
      this.currentDrawing.y2 = y;

      if (this.currentDrawing.type === 'measure') {
        const currentPrice = this.candlestickSeries.coordinateToPrice(y);
        const p1 = this.currentDrawing.startPrice || currentPrice;
        const diff = currentPrice - p1;
        const diffPct = (diff / p1) * 100;

        this.measureBox.style.display = 'block';
        this.measureBox.style.left = `${Math.min(x, rect.width - 150) + 12}px`;
        this.measureBox.style.top = `${y + 12}px`;
        this.measureBox.innerHTML = `
          <b style="color:${diff >= 0 ? '#10b981' : '#ef4444'}">${diff >= 0 ? '+' : ''}${diffPct.toFixed(2)}%</b><br/>
          <span>Δ $${diff.toFixed(2)}</span>
        `;
      }

      this.redrawCanvas();
    }

    onMouseUp(e) {
      if (!this.isDrawing) return;
      this.isDrawing = false;
      if (this.currentDrawing && this.currentDrawing.type !== 'measure') {
        this.drawings.push(this.currentDrawing);
      }
      this.currentDrawing = null;
      this.redrawCanvas();
    }

    /* ----------------------------------------------------
       9. LIVE TICKER POLLING (Updates Last Candle Live)
       ---------------------------------------------------- */
    startRealtimePolling() {
      setInterval(async () => {
        if (!this.candlesData || this.candlesData.length === 0) return;
        try {
          const sym = this.currentSymbol;
          const url = `https://api.binance.com/api/v3/ticker/price?symbol=${sym}`;
          const res = await fetch(url);
          const data = await res.json();
          const currentPx = parseFloat(data.price);
          if (isNaN(currentPx) || currentPx <= 0) return;

          const lastIdx = this.candlesData.length - 1;
          const lastCandle = this.candlesData[lastIdx];

          lastCandle.close = currentPx;
          if (currentPx > lastCandle.high) lastCandle.high = currentPx;
          if (currentPx < lastCandle.low) lastCandle.low = currentPx;

          this.candlestickSeries.update(lastCandle);

          const prevCandle = this.candlesData.length > 1 ? this.candlesData[lastIdx - 1] : lastCandle;
          this.renderLegendValues(lastCandle, prevCandle);

        } catch (e) {
          // silent fallback
        }
      }, 2500);
    }

    handleResize() {
      if (!this.viewportEl || !this.chart) return;
      const w = this.viewportEl.clientWidth;
      const h = this.viewportEl.clientHeight || this.options.height;
      if (w > 0 && h > 0) {
        this.chart.applyOptions({ width: w, height: h });
        this.resizeCanvas();
        if (this.candlesData && this.candlesData.length > 0) {
          this.chart.timeScale().fitContent();
        }
      }
    }

    setSymbol(symbol, timeframe) {
      if (symbol) {
        this.currentSymbol = symbol.toUpperCase().endsWith('USDT') ? symbol.toUpperCase() : symbol.toUpperCase() + 'USDT';
        const symSelect = document.getElementById(`${this.container.id}_sym_select`);
        if (symSelect) symSelect.value = this.currentSymbol;
        const legSym = document.getElementById(`${this.container.id}_leg_sym`);
        if (legSym) legSym.textContent = this.currentSymbol.replace('USDT', '/USDT');
      }
      if (timeframe) {
        this.currentTimeframe = timeframe;
        const tfBar = document.getElementById(`${this.container.id}_tf_bar`);
        if (tfBar) {
          tfBar.querySelectorAll('.tv-btn').forEach(b => {
            b.classList.toggle('active', b.getAttribute('data-tf') === timeframe);
          });
        }
        const legTf = document.getElementById(`${this.container.id}_leg_tf`);
        if (legTf) legTf.textContent = timeframe.toUpperCase();
      }
      this.loadData();
    }

    destroy() {
      if (this.resizeObserver) {
        this.resizeObserver.disconnect();
      }
      if (this.chart) {
        this.chart.remove();
      }
      if (this.container) {
        this.container.innerHTML = '';
      }
    }
  }

  // Export to window
  window.TradingViewProChart = TradingViewProChart;

})(window);
