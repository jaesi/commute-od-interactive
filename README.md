# commute_od_interactive

### 개요
  - 시청역(빅밸류 기준) 300m 이내에 있는 정류장으로 개별 정류장에서의 출근 소요시간 시각화를 Fast API와 JavaScript로 구현한 코드입니다.

### 실행방식
>1. requirements.txt를 통해 필요 라이브러리들을 설치 <br><br>
>2. CLI로  'uvicorn main:app --reload' 로 시작
> * 아래에 등록된 URL로 호스팅하셔야 네이버 API 접근 가능합니다 
>   * http://127.0.0.1:8000 (http:localhost:8000)
>   * http://10.10.12.85:15001