import pandas as pd
import ssl

# SSL証明書エラー回避
ssl._create_default_https_context = ssl._create_unverified_context

try:
    # Wikipediaから日経225銘柄一覧を取得
    url = "https://ja.wikipedia.org/wiki/%E6%97%A5%E7%B5%8C%E5%B9%B3%E5%9D%87%E6%A0%AA%E4%BE%A1"
    dfs = pd.read_html(url)
    
    # 構成銘柄のテーブルを探す (通常は "構成銘柄" を含むテーブル)
    target_df = None
    for df in dfs:
        # カラム名に "証券コード" や "銘柄名" が含まれているか確認
        # 実際のテーブル構造に合わせて調整が必要かもしれません
        # Wikipediaの構造が変わることもあるため、行数や内容で推測
        if len(df) >= 200 and ('コード' in df.columns or '証券コード' in df.columns or any(col for col in df.columns if 'コード' in str(col))):
             target_df = df
             break
        # カラム名が数字の場合もあるので、データ内容でチェック
        elif len(df) >= 200:
            # 最初の列が数字（コード）っぽいか
            try:
                first_val = str(df.iloc[0, 0])
                if first_val.isdigit() and len(first_val) == 4:
                    target_df = df
                    break
            except:
                pass

    if target_df is None:
        # もう少し緩い条件で探す (構成銘柄一覧は通常3列〜5列程度)
        for df in dfs:
            if len(df) >= 220: # 225銘柄以上あるはず
                target_df = df
                break

    if target_df is not None:
        # コードが含まれる列を特定する
        code_col = None
        for col in target_df.columns:
            # 文字列化してチェック
            sample = str(target_df[col].iloc[0])
            if sample.isdigit() and len(sample) == 4:
                code_col = col
                break
        
        if code_col is not None:
            codes = target_df[code_col].astype(str).tolist()
            # ".T" を付与
            formatted_codes = [f"{code}.T" for code in codes]
            print("FOUND_CODES_START")
            for code in formatted_codes:
                print(code)
            print("FOUND_CODES_END")
        else:
            print("Error: Could not identify code column.")
            print(target_df.head())
    else:
        print("Error: Could not find Nikkei 225 table.")

except Exception as e:
    print(f"Error: {e}")
