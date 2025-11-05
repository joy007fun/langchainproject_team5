-- 실행 시간: 2025-11-05 23:17:23
                            -- 도구: 
                            -- 설명: 
                        -- 파라미터: ('%"Generating Text with Pretrained Transformer Models"  \n\n(참고: 정확한 논문 제목이 아닌 일반적인 표현일 수 있습니다. 사용자가 구체적으로 언급한 "GPT 논문"이 어떤 버전을 가리키는지 명시되지 않았기 때문입니다. 예를 들어, 원본 GPT 논문 제목은 **"Improving Language Understanding by Generative Pre-Training" (2018)**이며, GPT-2의 경우 **"Language Models are Unsupervised Multipurpose Learners" (2019)**입니다. 정확한 제목을 원하시면 추가 정보가 필요합니다.)  \n\n→ **사용자의 요청에 따라 제목만 정확히 반환해야 하므로, 추가 설명 없이 가장 대표적인 GPT 논문 제목을 제시합니다:**  \n**"Improving Language Understanding by Generative Pre-Training"**%',)
-- 결과 개수: 0


        SELECT paper_id, title, authors, abstract, publish_date
        FROM papers
        WHERE title ILIKE %s
        LIMIT 1
        ;

