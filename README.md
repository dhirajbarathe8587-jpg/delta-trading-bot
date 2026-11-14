# Delta Exchange 24/7 Multi-Crypto Bot (EMA 9 & 15 Strategy)

हा बॉट डेल्टा एक्सचेंजवरील **टॉप 12 क्रिप्टोकरन्सी** एकाच वेळी 24/7 स्कॅन करतो आणि **EMA 9 व EMA 15 क्रॉसओव्हर** वर ऑटोमॅटिक ट्रेड्स घेतो.

---

### समाविष्ट असलेल्या क्रिप्टोकरन्सी (Watchlist):
1. **BTCUSD** (Bitcoin)
2. **ETHUSD** (Ethereum)
3. **SOLUSD** (Solana)
4. **XRPUSD** (Ripple)
5. **DOGEUSD** (Dogecoin)
6. **BNBUSD** (Binance Coin)
7. **ADAUSD** (Cardano)
8. **AVAXUSD** (Avalanche)
9. **LINKUSD** (Chainlink)
10. **SUIUSD** (Sui)
11. **NEARUSD** (Near Protocol)
12. **LTCUSD** (Litecoin)

---

### कार्यपद्धती (How it works):
1. **ऑल-कॉइन स्कॅनिंग:** बॉट दर 30 सेकंदांनी वरील सर्व 12 कॉईन्सचे चार्ट्स स्कॅन करतो.
2. **स्मार्ट एंट्री (Buy):** ज्या कॉईनवर **EMA 9 खालून येऊन EMA 15 ला वर क्रॉस करेल (Bullish Crossover)**, बॉट तात्काळ त्या कॉईनमध्ये BUY ट्रेड घेतो.
3. **मार्जिन प्रोटेक्शन (Max Active Trades = 1):** एका वेळी फक्त 1 ॲक्टिव्ह ट्रेड चालू राहतो, जेणेकरून तुमचे फंड्स सुरक्षित राहतील.
4. **ऑटोमॅटिक एक्झिट:**
   - **Take Profit:** **+1.5%** प्रॉफिट झाल्यावर एक्झिट.
   - **Stop Loss:** **-1.0%** वर रिस्क कंट्रोलसाठी एक्झिट.
   - **Trend Reversal (Bearish Cross):** ट्रेंड उलट फिरल्यास सेफ एक्झिट.
5. ट्रेड क्लोज झाल्यावर बॉट पुन्हा सर्व 12 कॉईन्स स्कॅन करायला सुरुवात करतो.

---

### फाईल्स:
* **config.py:** कॉईन्सची यादी (Watchlist), EMA, आणि Take Profit / Stop Loss सेटिंग्स.
* **trading_bot.log:** सर्व लाईव्ह ट्रेड्स आणि स्कॅन रिपोर्ट.
* **start_bot.bat:** एका क्लिकवर मॅन्युअली सुरू करण्यासाठी.
