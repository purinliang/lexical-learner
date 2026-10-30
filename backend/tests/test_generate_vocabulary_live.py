import json

import pytest

from lexical_learner.generate_vocabulary import generate_vocabulary


@pytest.mark.live
def test_generate_vocabulary_live():
    prompt = "我准备要去参加驾考，可是我不太熟悉车上常用的零件怎么说。"
    words = generate_vocabulary(prompt)

    assert isinstance(words, list)
    assert 1 <= len(words) <= 30
    assert all(isinstance(word, str) and word.strip() for word in words)

    print(json.dumps(words, ensure_ascii=False, indent=2))
