import urllib.request
import json
import ssl

def generate():
    url = "https://api.bithumb.com/public/ticker/ALL_KRW"
    headers = {'User-Agent': 'Mozilla/5.0'}
    req = urllib.request.Request(url, headers=headers)
    context = ssl._create_unverified_context()
    
    print("Fetching Bithumb data...")
    with urllib.request.urlopen(req, context=context) as res:
        data = json.loads(res.read().decode('utf-8'))
    
    tickers = []
    if data['status'] == '0000':
        for code in data['data'].keys():
            if code != 'date':
                tickers.append(f"BITHUMB:{code}KRW")
        
        tickers.sort()
        
        output_path = '/Users/jungsunghoon/Desktop/Desktop/bithumb_all_coins.txt'
        with open(output_path, 'w') as f:
            f.write('\n'.join(tickers))
        
        print(f"Success! Created {output_path} with {len(tickers)} coins.")
    else:
        print("Error fetching data")

if __name__ == "__main__":
    generate()
