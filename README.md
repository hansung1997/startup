Code Introduction [english]-

Captures a specific area of ​​the screen in real time and performs OCR (optical character recognition). Translates automatically or manually extracted text using the AI ​​translation API. Displays translation results in real-time or manually in a Tkinter overlay window. Developed for those who want to view English subtitles in real-time in Korean for games, videos, news, etc.

#Directory Structure

Details
---
Usage

After launching, select the desired translation area using the "Select Area" button or the menu. Click the "Translate Selection" button for automatic real-time translation (subtitles, etc.), or the "Translate Selection" button for manual translation. Drag the overlay window to resize it. Change the font size, translation API, transparency, and more with the settings button. Toggle the overlay with shortcut keys like ESC (you can specify a key by pressing the icon in the upper right corner). # Requires two clicks.

--Main Algorithm/Logic Description--

[OCR and Translation Preprocessing]

ocr.py

Image preprocessing (grayscale, blur, binarization, resizing, HSV masking) buffers sentences, checks for completeness (punctuation + prepositions, etc.), and compares translation cache for similarity (SequenceMatcher) to prevent duplicate translations.

translator.py

Selects APIs and processes only the parts that are called.

[UI]

app_ui.py #Main Menu UI

overlay.py

Tkinter-based overlay UI. Supports user operations such as "Settings," "Delete," "Translate," and "Reset Area."

--Future Improvement Directions--

OCR false positives/missing cases: Image quality improvement and additional preprocessing are required. Currently, dividing data into sentences using only ".", "?", and "!" produces significant noise. After checking for word-by-word duplication, attempting translation based on prepositions and conjunctions, excluding the three special characters mentioned above, resulted in less data noise.

Additional translation of long/connected sentences requires natural connection.

Google/DeepL API usage restrictions (403, timeout, etc.) #DeepL is currently unavailable due to expiration. It would be more efficient to develop a classic local translation tool and use it in the future.

Improved native (Windows) shortcut keys/global input events. In the shortcut key assignment section, we found cases where a single key press was required instead of a single press. Therefore, future replacement is inevitable.

When we first started the project, we aimed for a lightweight program. However, we added more features than expected, resulting in a three- to four-fold increase in size, diminishing its utility. Our goal is to further optimize the program through integration with C++.

[Console Command]

Details
There is currently no separate installation file; the library can be downloaded and used from the console.

<details>
<pre>
pip install pytesseract
pip install opencv-python
pip install numpy
pip install spacy
pip install mss
pip install keyboard
pip install pillow
pip install screeninfo
</pre>
</details>

---

코드 소개 -

화면의 특정 영역을 실시간으로 캡처하여 OCR(문자인식)을 수행
자동 또는 수동으로 추출된 텍스트를 AI 번역 API로 번역
Tkinter 오버레이(Overlay) 창에 번역 결과를 실시간/수동 표시
게임, 동영상, 뉴스 등 영어 자막을 실시간으로 한글로 보고 싶은 사람을 위해 개발

---

#디렉토리 구조

<details> 
<pre>OCR_Translator/
├── main.py                # 진입점, 전체 초기화/실행 관리
├── overlay.py             # 오버레이 UI 및 사용자 상호작용
├── ocr.py                 # OCR 텍스트 추출 및 전처리 로직
├── capture.py             # 화면 캡처 (mss, numpy, opencv 활용)
├── translator.py          # 번역 API (Google, DeepL 등)
├── local_translator.py    # ----현재 사용 안함---- [로컬 처리 부분]
├── spacy_trans.py         # ----현재 사용 안함---- [로컬 처리 부분]
├── select_area.py         # 마우스로 영역 선택 유틸리티
├── translation_cache.json # 번역/텍스트 캐시
├── config.py              # 설정/레이아웃 파일로 저장/불러오기
├── utils.py               # 좌표/해상도 데이터 변환 및 계산
├────── thread 
|      └── start_workers.py # 글자 인식 시 스레드  
├────── icons #아이콘 저장 
|      └──  ...
└── README.md              # 문서
</pre>
</details>
---

사용법

실행 후 “영역 선택” 버튼 또는 메뉴에서 원하는 번역 영역 지정
실시간 번역(자막 등)은 자동, 수동 번역은 ‘선택지 번역’ 버튼 클릭
오버레이 창 드래그로 크기 조절 가능
설정 버튼으로 폰트 크기, 번역 API, 투명도 등 변경 가능
ESC 등 단축키로 오버레이 토글 (오른쪽 상단 아이콘 누를시 키 지정 가능) # 두번정도 클릭해야 함.

---

--주요 알고리즘/로직 설명--

[OCR 및 번역 전처리 부분]

ocr.py

이미지를 전처리(그레이스케일, 블러, 이진화, 크기 조정, HSV 마스킹)
문장 단위로 버퍼링, “완결성(구두점+전치사 등)” 검사 후 번역
캐시와 유사도 비교(SequenceMatcher)로 중복 번역 방지

translator.py

API 선택, 호출하는 부분만 처리.

[UI부분]

app_ui.py #메인 메뉴 ui

overlay.py

Tkinter 기반 오버레이 UI
“설정”, “삭제”, “번역”, “영역 재설정” 등 사용자 조작 지원

---

--추후 개선 방향--


OCR 오탐/누락 케이스: 이미지 품질 향상, 전처리 추가 필요.
현재로서는 "." "?" "!" 로만 데이터를 나눠서 문장으로 나눴을 경우 노이즈가 심함.
단어 단위로 중복을 체크 후, 위의 특수문자 3개를 제외한 전치사 접속사를 기준으로 번역을 시도할 경우가 데이터의 노이즈가 적었음.  
긴 문장/연결 문장 자연스러운 연결 번역 추가 필요

구글/DeepL API 사용량 제한 이슈 (403, timeout 등) #현재 deepl은 기간 만료되어 사용 불가능.
추후에 로컬 전용으로 고전 번역기를 제작 후 사용하는것이 더 효율이 좋을 것으로 판단.

네이티브(윈도우) 단축키/전역 입력 이벤트 보완, 단축키를 지정하는 부분에서 한번으로 설정이 되지 않고 2~3번 눌러야 적용이 되는 케이스를 발견, 추후에 교체가 불가피할 것으로 판단.

프로젝트를 처음 시작했을 때, 가벼운 프로그램을 지향하면서 시작했으나.
생각보다 기능이 많이 추가되어 예상보다 용량이 3~4배로 높아져버려 그 효용성이 퇴색됐음.
추후에 c++과의 연계로 최적화를 하는 것을 목표.

---

[콘솔 명령어]

<details>
<pre>
pip install pytesseract
pip install opencv-python
pip install numpy
pip install spacy
pip install mss
pip install keyboard
pip install pillow
pip install screeninfo
</pre>
</details>
현재는 따로 설치 파일은 없고, 콘솔에서 해당 라이브러리 다운 받고 사용 가능.
