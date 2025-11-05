-- 실행 시간: 2025-11-05 15:22:54
                            -- 도구: 
                            -- 설명: 
                        -- 파라미터: ('%"Attention Is All You Need"%',)
-- 결과 개수: 0


        SELECT paper_id, title, authors, abstract, publish_date
        FROM papers
        WHERE title ILIKE %s
        LIMIT 1
        ;

