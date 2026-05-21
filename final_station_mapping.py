"""
Final compilation of all results.
"""
import json

print("=" * 70)
print("TASK 1: F-D0047 Dataset ID Mapping")
print("=" * 70)

print("""
HOURLY SERIES (逐1小時) - F-D0047-061 to F-D0047-091 (odd numbers only):
  F-D0047-061: 臺北市 (12 locations / districts)
  F-D0047-063: 臺北市 (12 locations) [duplicate/mirror of 061]
  F-D0047-065: 高雄市 (38 locations)
  F-D0047-067: 高雄市 (38 locations) [duplicate/mirror]
  F-D0047-069: 新北市 (29 locations)
  F-D0047-071: 新北市 (29 locations) [duplicate/mirror]
  F-D0047-073: 臺中市 (29 locations)
  F-D0047-075: 臺中市 (29 locations) [duplicate/mirror]
  F-D0047-077: 臺南市 (37 locations)
  F-D0047-079: 臺南市 (37 locations) [duplicate/mirror]
  F-D0047-081: 連江縣 (4 locations)
  F-D0047-083: 連江縣 (4 locations) [duplicate/mirror]
  F-D0047-085: 金門縣 (6 locations)
  F-D0047-087: 金門縣 (6 locations) [duplicate/mirror]
  F-D0047-089: 台灣 (22 locations = all counties summary)
  F-D0047-091: 台灣 (22 locations) [duplicate/mirror]
  F-D0047-093 to F-D0047-106: HTTP 404 (do not exist)

NOTE: Even-numbered IDs (062, 064, ...) all return HTTP 404.
NOTE: The hourly series ONLY covers: 臺北市, 高雄市, 新北市, 臺中市, 臺南市,
      連江縣, 金門縣, plus an all-Taiwan summary (22 locations).
      The remaining 15 counties ONLY have the 3-hourly series.

3-HOURLY SERIES (逐3小時) - F-D0047-001 to F-D0047-057 (odd numbers):
  F-D0047-001/003: 宜蘭縣 (12 locations)
  F-D0047-005/007: 桃園市 (13 locations)
  F-D0047-009/011: 新竹縣 (13 locations)
  F-D0047-013/015: 苗栗縣 (18 locations)
  F-D0047-017/019: 彰化縣 (26 locations)
  F-D0047-021/023: 南投縣 (13 locations)
  F-D0047-025/027: 雲林縣 (20 locations)
  F-D0047-029/031: 嘉義縣 (18 locations)
  F-D0047-033/035: 屏東縣 (33 locations)
  F-D0047-037/039: 臺東縣 (16 locations)
  F-D0047-041/043: 花蓮縣 (13 locations)
  F-D0047-045/047: 澎湖縣 (6 locations)
  F-D0047-049/051: 基隆市 (7 locations)
  F-D0047-053/055: 新竹市 (3 locations)
  F-D0047-057: 嘉義市 (2 locations)

  Missing from 3-hourly: 臺北市, 高雄市, 新北市, 臺中市, 臺南市
  → These 5 have HOURLY series instead (F-D0047-061+)
""")

print("=" * 70)
print("TASK 2: CODIS Station ID Mapping by County")
print("=" * 70)

print("""
COUNTY → BEST CODIS STATION (verified working for 2026-04)
stn_type=cwb for all 466/467 series; stn_type=auto_C0 for C0D series

臺北市:  466920  臺北 (TAIPEI) - PRIMARY ← confirmed working
臺北市:  466910  鞍部 (ANBU) - mountain alt 837m
臺北市:  466930  陽明山/竹子湖 (ZHUZIHU) - alt 607m

新北市:  466881  新北 (New Taipei) - PRIMARY ← stn replaced 466880
新北市:  466900  淡水 (TAMSUI) - coastal

基隆市:  466940  基隆 (KEELUNG) - PRIMARY

宜蘭縣:  467080  宜蘭 (YILAN) - PRIMARY

桃園市:  467050  新屋 (XINWU) - PRIMARY

新竹市:  C0D660  新竹市東區 - PRIMARY (stn_type=auto_C0)
         C0D670  海天一線 (alt: coastal), C0D680  香山濕地 also work
         NOTE: Retired synoptic 467570 (新竹市) has NO current replacement in cwb series

新竹縣:  467571  新竹 (HSINCHU) - PRIMARY

苗栗縣:  467280  後龍 (Houlong) - PRIMARY

臺中市:  467490  臺中 (TAICHUNG) - PRIMARY

彰化縣:  467270  田中 (TianZhong) - PRIMARY

南投縣:  467650  日月潭 (SUN MOON LAKE) - PRIMARY
         467550  玉山 (YUSHAN) - high altitude 3844m

雲林縣:  467290  古坑 (Gukeng) - PRIMARY

嘉義市:  467480  嘉義 (CHIAYI) - PRIMARY

嘉義縣:  467530  阿里山 (ALISHAN) - PRIMARY (alt 2413m)

臺南市:  467410  臺南 (TAINAN) - PRIMARY
         467420  永康 (YONGKANG) also works

高雄市:  467441  高雄 (Kaohsiung) - PRIMARY

屏東縣:  467590  恆春 (HENGCHUN) - PRIMARY

臺東縣:  467660  臺東 (TAITUNG) - PRIMARY
         467610  成功 (CHENGGONG), 467540  大武 (DAWU) also work

花蓮縣:  466990  花蓮 (HUALIEN) - PRIMARY

澎湖縣:  467350  澎湖 (PENGHU) - PRIMARY
         467300  東吉島 (DONGJIDAO) also works

金門縣:  467110  金門 (KINMEN) - PRIMARY

連江縣:  467990  馬祖 (MATSU) - PRIMARY
""")

print("=" * 70)
print("IMPORTANT NOTES")
print("=" * 70)
print("""
1. Initial guesses for station IDs were almost all WRONG. The 466/467 numbering
   does NOT correspond intuitively to geography. Always verify via C-B0074-001.

2. Several commonly assumed stations are now retired:
   - 466880 板橋 (新北市) → replaced by 466881 新北
   - 467060 蘇澳 (宜蘭縣) → replaced by C0UB10 (auto station)
   - 467570 新竹 (新竹市) → NO cwb replacement; use auto_C0 C0D660
   - 467440 高雄 (高雄市) → replaced by 467441 高雄
   - 467770 梧棲 (臺中市) → replaced by C0FA30 梧棲 (auto)

3. Radar stations (466850 五分山, 467790 墾丁) return no temperature data.

4. 新竹市 has no current synoptic (cwb) station. Use stn_type=auto_C0 with
   C0D660 (新竹市東區) for auto-station temperature data.

5. 467550 玉山 is at 3844m altitude - not representative of 南投縣 flatland.
   467650 日月潭 (748m) is better for general South Nantou.

6. In the F-D0047 hourly series: odd IDs are forecast datasets,
   same county appears twice (e.g., 061 and 063 both = 臺北市).
   This appears to be two different data ranges or time windows.
""")
