import spacy

nlp = spacy.load("en_core_web_sm")


def analyze_and_reorder(sentence):
    doc = nlp(sentence)

    print(f"{'단어':<15} {'원형(lemma)':<15} {'품사(POS)':<10} {'의존관계(dep)':<15} {'상위단어(head)':<15}")
    print("-" * 80)

    # 분석 정보 출력
    for token in doc:
        print(f"{token.text:<15} {token.lemma_:<15} {token.pos_:<10} {token.dep_:<15} {token.head.text:<15}")

    # 핵심 요소 추출
    subject = ""
    main_verb = ""
    aux_verbs = []
    objects = []
    prepositional_phrases = []

    for token in doc:
        if token.dep_ == "nsubj":
            subject = token.text
        elif token.dep_ == "ROOT":
            main_verb = token.lemma_
        elif token.dep_ == "aux" or token.dep_ == "auxpass":
            aux_verbs.append(token.text)
        elif token.dep_ == "dobj" or token.dep_ == "pobj":
            objects.append(token.text)
        elif token.dep_ == "prep":
            prep_phrase = " ".join([child.text for child in token.subtree])
            prepositional_phrases.append(prep_phrase)

    # 임시 번역 사전 (데모용)
    ko_dict = {
        "she": "그녀는",
        "he": "그는",
        "wait": "기다렸다",
        "waiting": "기다리고 있었다",
        "have": "가지고 있었다",
        "been": "되어 있었다",
        "me": "나를",
        "for": "~을 위해",
        "at": "~에서",
        "stop": "정류장",
        "bus": "버스"
    }

    # 한국어형 어순 재배열 예시 (S + 전치사구 + 목적어 + V)
    translated = []
    if subject:
        translated.append(ko_dict.get(subject.lower(), subject))
    if prepositional_phrases:
        translated.extend(prepositional_phrases)  # 실제로는 번역 필요
    if objects:
        translated.append(ko_dict.get(objects[0].lower(), objects[0]))
    if main_verb:
        if "been" in aux_verbs or "had" in aux_verbs:
            translated.append("기다리고 있었다")
        else:
            translated.append(ko_dict.get(main_verb.lower(), main_verb))

    print("\n한국어형 재배열 결과:")
    print(" ".join(translated))


# 테스트
sentence = "She had been waiting for me at the bus stop."
analyze_and_reorder(sentence)
