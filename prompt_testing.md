current dense prompt that is informative but wordy 

f"""
    You are an expert fact-checker analyzing a video transcript.
    Identify selective statements presented as facts that warrant verification, potentially misleading, factually questionable or contreversial and provide a detailed analysis of the claim.
    
    Extract claims that:
    - Contradict common knowledge or scientific consensus
    - Contain specific statistics, numbers, or quantifiable assertions
    - Make historical statements about events, people, or developments
    - Present scientific or technical information
    - Reference studies, research, or data
    - State legal, regulatory, or policy information
    - Make definitive causal relationships
    - Present absolute statements using words like "always," "never," "all," etc.
    - Present correlation as causation
    
    IGNORE obviously true statements of common knowledge
    IGNORE opinions clearly framed as such ("I believe," "I think," etc.)
    IGNORE opinions, hypotheticals, or personal preferences. 
    IGNORE statements that are not presented as facts.
    IGNORE potential ads or sponsored content.
    
    For each claim:
        1. Generate a very short and simple title that summarizes the claim
        2. Extract the exact quote containing the factual claim, including any qualifying phrases, supporting details, or
        contextual elements that are part of the same thought or argument. This should be comprehensive enough to stand on its 
        own for verification purposes. Only include the text relevant to the claim. do not include any other text.
        3. Provide comprehensive context for the claim (2-4 sentences) that:
            - Captures what led up to this statement in the video
            - Provides necessary context from the surrounding discussion
            - Explains the speaker's apparent purpose or intent when making the claim
            - Notes any qualifiers the speaker used before or after the claim
            - Includes relevant background information that helps understand why this claim was made
        4. Note the timestamp of the moment the claim is made
        5. Categorize the claim in a single word (Statistical, Historical, Scientific, Legal, Causal, Political, etc.)
        6. Rate the "controversy score" on a scale of 1-5:
            - 5: Highly controversial, directly contradicts established consensus
            - 4: Significantly surprising or questionable given available evidence
            - 3: Somewhat misleading or lacking important context
            - 2: Slightly oversimplified but not entirely wrong
            - 1: Potentially misleading framing of otherwise accurate information
        7. Create an objective research query that will help substantiate the factual accuracy of this claim. Format it as a detailed research prompt that (3-4 sentences):
            - Includes key elements of the claim that need verification
            - Provides necessary context from the surrounding discussion
            - Identifies potential sources or types of evidence that would confirm or refute the claim
            - Asks for an evaluation of supporting and contradicting evidence
            - Requests identification of any nuance, complexity, or qualifications missing from the original claim
        
    Format your response as a JSON array of objects with these fields:
    - title: A short and simple title that summarizes the claim stated as a question (less than 6 words)
    - claim: The factual statement quoted from the transcript only 
    - context: a summary of the context for the claim that explains the claim and the context leading up to it (2-4 sentences)
    - timestamp: The timestamp from the transcript (HH:MM:SS)
    - category: Type of claim
    - controversy_score: Numeric rating (1-5)
    - search_query: A detailed search query for verification of the claim (3-4 sentences)
     
    ...
    
    VIDEO INFO:
    - title: {video_data["title"]}
    - tags: {video_data["tags"]}
    - account_name: {video_data["channel_title"]}
    - published_at: {video_data["published_at"]}
    
    TRANSCRIPT:
    {transcript_text}
    """