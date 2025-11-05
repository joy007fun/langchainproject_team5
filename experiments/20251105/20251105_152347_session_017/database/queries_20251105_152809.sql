-- SQL Queries Log
-- Generated at: 2025-11-05T15:28:09.563649

-- Query 1
-- 실행 시간: 2025-11-05 15:25:54
                            -- 도구: 
                            -- 설명: 
                        -- 파라미터: ('%Attention Is All You Need%',)
-- 결과 개수: 1


        SELECT paper_id, title, authors, abstract, publish_date
        FROM papers
        WHERE title ILIKE %s
        LIMIT 1
        ;

-- Query 2
-- 실행 시간: 2025-11-05 15:26:49
                            -- 도구: 
                            -- 설명: 
                        -- 파라미터: ('%GPT 논문 찾아서 요약해줘\n\n논문 제목: Generative Pre-trained Transformer (GPT) 관련 논문\n\n(※ 실제 정확한 논문 제목은 GPT-1/GPT-2/GPT-3 등 버전에 따라 다릅니다. 예시: \n- "Improving Language Understanding by Generative Pre-Training" (GPT-1)\n- "Language Models are Unsupervised Multipurpose Learners" (GPT-2)\n- "Language Models are Few-Shot Learners" (GPT-3))\n\n정확한 논문명을 요청하려면 특정 GPT 버전을 명시해 주세요.) \n\n(현재 지시사항에 따라 제목만 반환해야 하므로 추가 설명 생략) \n\nGenerative Pre-trained Transformer (GPT) 관련 논문%',)
-- 결과 개수: 0


        SELECT paper_id, title, authors, abstract, publish_date
        FROM papers
        WHERE title ILIKE %s
        LIMIT 1
        ;

