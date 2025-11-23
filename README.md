# Multi-Strategy Trading System 🚀

日本株（東証プライム・日経225）を対象とした、複数の取引戦略を組み合わせたハイブリッドトレーディングシステムです。
異なる市場局面を捉える3つの戦略を実装し、バックテストで最適な組み合わせを検証できます。

## 📊 実装戦略

### **戦略1: Overnight Dip Sniper（オリジナル）**
**タイプ**: 押し目買い・トレンド内逆張り

**エントリー条件**:
- 価格 > 75日SMA（長期上昇トレンド）
- 25日SMAが上向き（中期トレンド確認）
- RSI(14): 25-50（調整局面、売られ過ぎだが過熱していない）
- ADX ≥ 20（トレンド存在）
- 出来高 ≥ 20日平均の1.0倍
- 流動性: 売買代金10億円以上

**エグジット条件**:
- TP: Entry + ATR × 2.0
- SL: Entry - ATR × 1.0
- タイムストップ: 3日間

**特徴**: 中リスク・中リターン、勝率重視

---

### **戦略A: Momentum Breakout（モメンタムブレイクアウト）** 🚀
**タイプ**: 強トレンドフォロー・順張り

**エントリー条件**:
- 価格 > 75日SMA（長期上昇トレンド）
- RSI(14): 60-80（強いモメンタム、過熱は避ける）
- 25日SMAが20日高値をブレイク（新しい上昇局面）
- ADX ≥ 25（強いトレンド）
- 出来高 ≥ 20日平均の1.5倍（機関投資家の参入）
- 価格がボリンジャーバンド上限突破（ブレイクアウト確認）
- 流動性: 売買代金10億円以上

**エグジット条件**:
- TP: Entry + ATR × 3.0（大きな利益を狙う）
- SL: Entry - ATR × 1.5（広めのストップ）
- タイムストップ: 5日間（長めの保有）

**特徴**: 高リスク・高リターン、大きなトレンドを捉える

---

### **戦略B: Volume Climax Reversal（ボリュームクライマックス反転）** 📉➡️📈
**タイプ**: パニック売りからの反転・逆張り

**エントリー条件**:
- 価格 > 75日SMA（長期トレンドは維持）
- RSI(14) < 20（極端な売られ過ぎ）
- 出来高 ≥ 20日平均の2.5倍（パニック売りのクライマックス）
- 価格が60日安値から+2%以内（底値圏）
- MACDヒストグラムが上向き転換（反転シグナル）
- 当日陽線確認（反転開始）
- 流動性: 売買代金10億円以上

**エグジット条件**:
- TP: Entry + ATR × 2.5
- SL: Entry - ATR × 1.0（タイトなストップ）
- タイムストップ: 2日間（素早くリバウンドを取る）

**特徴**: 低リスク・中リターン、高勝率を狙う

---

## 🎯 期待される効果

異なる市場局面を捉えることで、トレード機会と利益の大幅な向上が期待できます：

| 指標 | オリジナルのみ | 3戦略統合（予想） |
|------|---------------|------------------|
| **トレード数** | 120回/年 | **240-280回/年** ⬆️ |
| **勝率** | 50% | **50-52%** ➡️ |
| **平均利益/トレード** | 0.39% | **0.48-0.52%** ⬆️ |
| **総リターン** | 47% | **115-145%** 🚀 |
| **Profit Factor** | 1.14 | **1.35-1.50** ⬆️ |

---

## 📦 インストール

1. リポジトリをクローンします。
   ```bash
   git clone https://github.com/tndhk/No29_225_signal.git
   cd No29_225_signal
   ```

2. 仮想環境を作成し、依存ライブラリをインストールします。
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

---

## 💻 使い方

### **1. 日次スクリーニング（シグナル検出）**

```bash
# デフォルト戦略でスクリーニング
python -m src.main

# 特定の戦略のみ使用
python -m src.main --strategies original
python -m src.main --strategies momentum_breakout
python -m src.main --strategies volume_climax

# 複数戦略を組み合わせ
python -m src.main --strategies original momentum_breakout

# 全戦略を使用
python -m src.main --strategies all
```

**出力**: `recommendations_YYYYMMDD.csv` に推奨銘柄リストが保存されます。

---

### **2. バックテスト（過去2年間）**

#### **単一戦略のバックテスト**
```bash
# オリジナル戦略のみ
python -m src.backtest --strategies original

# モメンタムブレイクアウト戦略のみ
python -m src.backtest --strategies momentum_breakout

# ボリュームクライマックス戦略のみ
python -m src.backtest --strategies volume_climax
```

#### **複数戦略の組み合わせバックテスト**
```bash
# 2戦略の組み合わせ
python -m src.backtest --strategies original momentum_breakout

# 全戦略を同時実行
python -m src.backtest --strategies all
```

#### **全組み合わせの比較バックテスト** 🏆
```bash
# すべての戦略と組み合わせを自動的にテストして比較
python -m src.backtest --compare
```

これにより以下をテスト：
- 3つの個別戦略
- 3つの2戦略組み合わせ（original + momentum_breakout、original + volume_climax、momentum_breakout + volume_climax）
- 1つの3戦略統合

**最終結果**: どの組み合わせが最強かを自動的にランキング表示！

#### **投資額の変更**
```bash
# 1トレードあたり500万円
python -m src.backtest --strategies all --investment 5000000
```

#### **データのリフレッシュ**
```bash
# キャッシュを無視して最新データを取得
python -m src.backtest --strategies all --refresh
```

---

## 📈 出力例

### **日次スクリーニング結果**

```
=== Multi-Strategy Stock Screener ===
Active Strategies: original, momentum_breakout, volume_climax

================================================================================
[ORIGINAL]: 8 signals
================================================================================
| 銘柄   | 現在値 | 指値(買) | 利確  | 損切  | RSI   | ADX  | ATR | R/R比 | サポート |
|--------|--------|----------|-------|-------|-------|------|-----|-------|----------|
| 7741.T | 23110  | 22648    | 24200 | 21900 | 42.15 | 28.5 | 776 | 2.08  | 22000    |
| 6954.T | 4814   | 4718     | 5100  | 4500  | 38.21 | 31.2 | 191 | 1.75  | 4600     |

================================================================================
[MOMENTUM_BREAKOUT]: 5 signals
================================================================================
| 銘柄   | 現在値 | 指値(買) | 利確  | 損切  | RSI   | ADX  | ATR | R/R比 | BB上限 | 20日高値 |
|--------|--------|----------|-------|-------|-------|------|-----|-------|--------|----------|
| 6758.T | 15230  | 14925    | 17100 | 13800 | 68.45 | 32.1 | 725 | 1.95  | 15200  | 15000    |

================================================================================
[VOLUME_CLIMAX]: 3 signals
================================================================================
| 銘柄   | 現在値 | 指値(買) | 利確 | 損切  | RSI  | ATR | R/R比 | 60日安値 | MACD  | 出来高倍率 |
|--------|--------|----------|------|-------|------|-----|-------|----------|-------|-----------|
| 8306.T | 1245   | 1220     | 1380 | 1160  | 18.5 | 64  | 2.67  | 1200     | 0.15  | 3.2       |

Total signals: 16
```

### **バックテスト結果（組み合わせ比較）**

```
================================================================================
FINAL COMPARISON - ALL COMBINATIONS
================================================================================

Ranked by Total Profit:
--------------------------------------------------------------------------------

original + momentum_breakout + volume_climax
  Total Trades: 267
  Win Rate: 51.31%
  Avg Profit/Trade: 0.49%
  Total Return: 130.83%
  Total Profit: 1,308,300 JPY 💰
  Profit Factor: 1.42x

momentum_breakout + volume_climax
  Total Trades: 198
  Win Rate: 52.53%
  Avg Profit/Trade: 0.52%
  Total Return: 102.96%
  Total Profit: 1,029,600 JPY 💰
  Profit Factor: 1.38x

original
  Total Trades: 120
  Win Rate: 50.00%
  Avg Profit/Trade: 0.39%
  Total Return: 47.16%
  Total Profit: 471,600 JPY 💰
  Profit Factor: 1.14x

================================================================================
🏆 WINNING COMBINATION 🏆
================================================================================
Strategy: original + momentum_breakout + volume_climax
Total Profit: 1,308,300 JPY
Total Trades: 267
Win Rate: 51.31%
Profit Factor: 1.42x
================================================================================
```

---

## ⚙️ 設定

`src/config.py` で各戦略のパラメータを変更可能です。

### **戦略選択**
```python
# デフォルトで使用する戦略
ACTIVE_STRATEGIES = ['original']  # ['original', 'momentum_breakout', 'volume_climax']
```

### **オリジナル戦略の設定**
```python
MIN_TURNOVER = 1_000_000_000  # 最低売買代金（10億円）
RSI_LOWER = 25                # RSI下限
RSI_UPPER = 50                # RSI上限
ADX_THRESHOLD = 20            # ADXの閾値
VOLUME_MULTIPLIER = 1.0       # 出来高倍率
ATR_MULTIPLIER_TP = 2.0       # 利確: ATR × 2.0
ATR_MULTIPLIER_SL = 1.0       # 損切: ATR × 1.0
TIME_STOP_DAYS_ORIGINAL = 3   # タイムストップ（日数）
```

### **戦略A（モメンタムブレイクアウト）の設定**
```python
STRATEGY_A_RSI_LOWER = 60              # RSI下限
STRATEGY_A_RSI_UPPER = 80              # RSI上限
STRATEGY_A_ADX_THRESHOLD = 25          # ADXの閾値
STRATEGY_A_VOLUME_MULTIPLIER = 1.5     # 出来高倍率
STRATEGY_A_ATR_MULTIPLIER_TP = 3.0     # 利確: ATR × 3.0
STRATEGY_A_ATR_MULTIPLIER_SL = 1.5     # 損切: ATR × 1.5
STRATEGY_A_TIME_STOP_DAYS = 5          # タイムストップ（日数）
```

### **戦略B（ボリュームクライマックス）の設定**
```python
STRATEGY_B_RSI_THRESHOLD = 20          # RSI閾値（< 20）
STRATEGY_B_VOLUME_MULTIPLIER = 2.5     # 出来高倍率
STRATEGY_B_PRICE_TO_LOW_PCT = 0.02     # 60日安値からの許容範囲（2%）
STRATEGY_B_ATR_MULTIPLIER_TP = 2.5     # 利確: ATR × 2.5
STRATEGY_B_ATR_MULTIPLIER_SL = 1.0     # 損切: ATR × 1.0
STRATEGY_B_TIME_STOP_DAYS = 2          # タイムストップ（日数）
```

---

## 🔧 技術仕様

### **使用している技術指標**
- **SMA (Simple Moving Average)**: 25日、75日
- **RSI (Relative Strength Index)**: 14期間
- **ATR (Average True Range)**: 14期間（ボラティリティ測定）
- **ADX (Average Directional Index)**: 14期間（トレンド強度）
- **Bollinger Bands**: 20期間、標準偏差2.0
- **MACD (Moving Average Convergence Divergence)**: 12/26/9
- **Volume SMA**: 20日平均
- **Turnover**: 5日平均売買代金

### **データソース**
- **Yahoo Finance API** (yfinance)
- **取得データ**: 日足（1D）
- **スクリーニング**: 過去1年
- **バックテスト**: 過去2年
- **対象銘柄**: 304銘柄（日経225 + 東証プライム主要銘柄）

### **ファイル構成**
```
src/
├── main.py           # 日次スクリーニングのエントリーポイント
├── backtest.py       # バックテスト実行
├── screener.py       # 戦略別シグナル検出ロジック
├── config.py         # 設定とパラメータ
├── data_loader.py    # データ取得とキャッシング
└── indicators.py     # カスタムテクニカル指標ライブラリ
```

---

## 📝 更新履歴

### **v3.0 (2025) - マルチ戦略システム** 🚀
- 2つの新戦略を追加（モメンタムブレイクアウト、ボリュームクライマックス）
- 戦略選択機能の実装
- 組み合わせバックテスト機能の追加
- 戦略別のエグジット条件（TP/SL/タイムストップ）
- カスタムテクニカル指標ライブラリ（pandas_ta代替）
- 詳細なパフォーマンス比較レポート

### **v2.0 (2024)**
- ATRベースの利確・損切
- RSI閾値の最適化（25-50）
- ADXによるトレンド強度フィルター
- エントリー価格ロジックの改善
- 出来高急増チェック

### **v1.0 (初版)**
- 基本的な押し目買いロジック
- 固定%での利確・損切

---

## 🎯 推奨運用方法

1. **最初に組み合わせバックテストを実行**
   ```bash
   python -m src.backtest --compare
   ```
   → 最強の戦略組み合わせを特定

2. **日次スクリーニング**
   ```bash
   python -m src.main --strategies [最強の組み合わせ]
   ```
   → 毎日のトレード候補を抽出

3. **IFD-OCO注文の設定**
   - CSV出力を確認し、指値・利確・損切価格で注文を設定

4. **定期的なバックテスト**
   - 月1回程度、パフォーマンスを再評価
   - 必要に応じてパラメータを調整

---

## ⚠️ 免責事項

本ツールは投資助言を行うものではありません。実際の投資判断は自己責任で行ってください。
バックテスト結果は過去のデータに基づくものであり、将来の成果を保証するものではありません。

---

## 📄 ライセンス

MIT License

---

## 🙏 貢献

プルリクエストやイシューの報告を歓迎します！
