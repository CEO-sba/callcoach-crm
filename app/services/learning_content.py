"""
CallCoach CRM - SBA Learning Academy Content & Module Engine

Full curriculum with interactive modules, quizzes, mock call scenarios,
scoring rubrics, and certification tracking based on the SBA Sales Trainer Playbook.
"""

# ---- MODULE DEFINITIONS ----

LEARNING_MODULES = [
    {
        "id": "mod_01_opening",
        "order": 1,
        "title": "Phase 1: The Opening",
        "subtitle": "Build Trust in the First 15 Seconds",
        "description": "Learn the SBA Opening structure: Name > Introduction > Inquiry > Permission. Master how to make a strong first impression that builds instant trust with patients.",
        "duration_minutes": 20,
        "category": "5_phase_framework",
        "icon": "hand-wave",
        "color": "#3B82F6",
        "learning_objectives": [
            "Use the patient's name immediately instead of 'sir/madam'",
            "Follow the Name > Introduction > Inquiry > Permission structure",
            "Reference the patient's original inquiry to build context",
            "Ask permission before proceeding to build respect",
            "Eliminate robotic greetings and create conversational warmth"
        ],
        "key_concepts": [
            {
                "title": "Why Names Matter",
                "content": "People respond better when they hear their name. Using 'sir sir sir' instead of the patient's name signals that you don't care about them as an individual. The patient's name is the single most important word in any sales conversation."
            },
            {
                "title": "The Opening Structure",
                "content": "Every opening must follow this sequence: (1) Use the patient name, (2) Introduce yourself and the clinic, (3) Reference their specific inquiry, (4) Ask permission to talk. Example: 'Hi Rahul, this is Meenu from Dr K's Clinic. You had inquired about Botox yesterday. Is this a good time to talk?'"
            },
            {
                "title": "Bad vs Good Openings",
                "content": "Bad: 'Hello sir this is ___ clinic we provide treatments.' This is robotic, impersonal, and immediately puts the patient in control. Good: 'Hi Rahul, this is Meenu from Dr K's Clinic. You had inquired about Botox yesterday. Is this a good time to talk?' This is personal, contextual, and respectful."
            },
            {
                "title": "Permission Creates Trust",
                "content": "Asking 'Is this a good time to talk?' shows respect. It creates a micro-commitment. When the patient says yes, they are psychologically invested in the conversation. Never skip this step."
            }
        ],
        "common_mistakes": [
            "Starting with 'Hello sir' instead of using the patient's actual name",
            "Launching into treatment details without any introduction",
            "Not referencing the patient's specific inquiry",
            "Skipping the permission step and diving into sales mode",
            "Reading from a script in a flat, monotone voice"
        ],
        "practice_exercises": [
            {
                "type": "script_practice",
                "title": "Rewrite the Opening",
                "instruction": "You receive a lead named Priya who inquired about laser hair removal yesterday. Write your opening line using the Name > Introduction > Inquiry > Permission structure.",
                "sample_answer": "Hi Priya, this is [Your Name] from [Clinic Name]. You had inquired about laser hair removal yesterday. Is this a good time to talk?"
            },
            {
                "type": "spot_the_mistake",
                "title": "What's Wrong Here?",
                "instruction": "Identify all mistakes in this opening: 'Hello sir, this is ABC Clinic. We do all types of skin treatments. Would you like to book an appointment?'",
                "sample_answer": "Mistakes: (1) Used 'sir' instead of patient name, (2) Generic introduction without staff name, (3) No reference to specific inquiry, (4) Jumped straight to appointment booking without discovery, (5) No permission question."
            }
        ],
        "quiz": [
            {
                "id": "q1",
                "question": "What is the correct opening structure according to the SBA method?",
                "options": [
                    "Treatment > Price > Booking",
                    "Name > Introduction > Inquiry > Permission",
                    "Hello > Clinic Name > Services > Close",
                    "Greeting > Treatment List > Discount Offer"
                ],
                "correct_answer": 1,
                "explanation": "The SBA Opening structure is Name > Introduction > Inquiry > Permission. This builds trust and shows the patient you remember them specifically."
            },
            {
                "id": "q2",
                "question": "Why should you use the patient's name instead of 'sir' or 'madam'?",
                "options": [
                    "It's just formal etiquette",
                    "People respond better when they hear their name, it signals personal attention",
                    "It saves time during the call",
                    "It is required by law"
                ],
                "correct_answer": 1,
                "explanation": "People respond better when they hear their name. Using 'sir sir sir' signals you don't care about them as an individual. The name is the most important word in a sales conversation."
            },
            {
                "id": "q3",
                "question": "What should you do IMMEDIATELY after introducing yourself?",
                "options": [
                    "List all available treatments",
                    "Ask about their budget",
                    "Reference their specific inquiry",
                    "Offer a discount"
                ],
                "correct_answer": 2,
                "explanation": "After introducing yourself, immediately reference their specific inquiry. This shows you prepared for the call and care about their specific need, not just making a generic sales pitch."
            },
            {
                "id": "q4",
                "question": "Why is asking 'Is this a good time to talk?' important?",
                "options": [
                    "It's just politeness with no real impact",
                    "It creates a micro-commitment and builds respect and trust",
                    "It gives you time to check your notes",
                    "It helps you avoid wasting time on uninterested people"
                ],
                "correct_answer": 1,
                "explanation": "Asking permission creates a micro-commitment. When the patient says 'yes', they become psychologically invested in the conversation. It also signals respect, which builds trust from the very first moment."
            }
        ],
        "mock_scenarios": [
            {
                "id": "mock_01_01",
                "title": "New Botox Inquiry",
                "patient_profile": "Anjali, 34, inquired about Botox for forehead wrinkles yesterday via Instagram ad",
                "patient_personality": "Busy professional, slightly hesitant, first time considering Botox",
                "opening_context": "This is a follow-up call to her Instagram inquiry",
                "evaluation_criteria": ["Used patient name", "Introduced self and clinic", "Referenced Botox inquiry", "Asked permission to talk", "Tone was warm and conversational"]
            },
            {
                "id": "mock_01_02",
                "title": "Hair Transplant Inquiry",
                "patient_profile": "Vikram, 28, filled a form on the website about hair transplant pricing 2 days ago",
                "patient_personality": "Price-sensitive, comparing multiple clinics, anxious about the procedure",
                "opening_context": "Second attempt at calling, first call went to voicemail",
                "evaluation_criteria": ["Used patient name", "Introduced self and clinic", "Referenced hair transplant inquiry", "Acknowledged this is a follow-up attempt", "Asked permission to talk"]
            }
        ]
    },
    {
        "id": "mod_02_problem_discovery",
        "order": 2,
        "title": "Phase 2: Problem Discovery",
        "subtitle": "Understand Before You Sell",
        "description": "Master the art of asking discovery questions that uncover the patient's real problem, motivations, and desired outcomes. Learn why selling before discovering is the biggest conversion killer.",
        "duration_minutes": 25,
        "category": "5_phase_framework",
        "icon": "search",
        "color": "#10B981",
        "learning_objectives": [
            "Ask open-ended discovery questions that reveal the patient's real problem",
            "Understand the difference between surface concerns and root motivations",
            "Let the patient talk without interrupting",
            "Avoid the temptation to pitch treatments during discovery",
            "Use discovery to naturally transition into mini diagnosis"
        ],
        "key_concepts": [
            {
                "title": "Why Discovery Comes First",
                "content": "If staff immediately starts selling treatments, the patient loses interest. Problem discovery must come before selling. The patient needs to feel understood before they will trust your recommendation. When you understand their problem deeply, your recommendation becomes a solution, not a sales pitch."
            },
            {
                "title": "The Three Discovery Questions",
                "content": "Every discovery phase should include variations of these three questions: (1) What concerns are you facing? (2) What made you inquire? (3) What result are you hoping for? These questions uncover the problem, the trigger, and the desired outcome."
            },
            {
                "title": "Let the Patient Talk",
                "content": "The trainer must emphasize: let the patient talk. Do not interrupt. When the patient is talking about their problem, they are convincing themselves they need a solution. Every word they speak increases their emotional investment in finding a fix."
            },
            {
                "title": "Discovery is Not Interrogation",
                "content": "Discovery should feel like a caring conversation, not a police interrogation. Ask one question at a time. Listen to the answer. Show genuine interest. Then ask the next question based on what they said, not from a pre-planned list."
            }
        ],
        "common_mistakes": [
            "Jumping to treatment recommendations after the patient mentions a concern",
            "Asking closed questions that get yes/no answers instead of open exploration",
            "Interrupting the patient mid-sentence to add information",
            "Asking multiple questions at once, confusing the patient",
            "Not listening to the answer and asking unrelated follow-up questions"
        ],
        "practice_exercises": [
            {
                "type": "script_practice",
                "title": "Discovery Question Set",
                "instruction": "A patient named Ravi says he is worried about hair loss. Write 3 discovery questions you would ask to understand his problem deeply.",
                "sample_answer": "1. 'Ravi, can you tell me more about when you first started noticing the hair loss?' 2. 'What made you decide to look into treatment options now?' 3. 'What kind of result would make you feel satisfied?'"
            },
            {
                "type": "spot_the_mistake",
                "title": "Too Fast to Pitch",
                "instruction": "Patient says: 'I have been losing hair for 2 years.' Staff responds: 'We have an excellent PRP treatment for Rs 15,000 per session.' What went wrong and what should they have said instead?",
                "sample_answer": "Mistake: Staff jumped straight to a treatment pitch with pricing before understanding the patient's full situation. Better response: '2 years, that must be concerning. Have you tried any treatments before? What were the results like?' This continues discovery and makes the patient feel heard."
            }
        ],
        "quiz": [
            {
                "id": "q1",
                "question": "What happens when staff immediately starts selling treatments?",
                "options": [
                    "Patient gets excited about the solution",
                    "Patient loses interest because they don't feel heard",
                    "Patient asks for a discount",
                    "Nothing significant changes"
                ],
                "correct_answer": 1,
                "explanation": "When staff immediately starts selling, the patient loses interest. They feel the clinic only cares about revenue, not about them. Problem discovery must come before any recommendation."
            },
            {
                "id": "q2",
                "question": "Which set of questions best represents the SBA discovery approach?",
                "options": [
                    "'What is your budget? When can you come in? Which treatment do you want?'",
                    "'What concerns are you facing? What made you inquire? What result are you hoping for?'",
                    "'Have you heard of our clinic? We have the best doctor. Can I book you today?'",
                    "'What treatment are you looking for? We have a discount this week.'"
                ],
                "correct_answer": 1,
                "explanation": "The SBA discovery questions focus on understanding the problem, the trigger, and the desired outcome. These help you understand the patient deeply before making any recommendation."
            },
            {
                "id": "q3",
                "question": "During discovery, the patient starts explaining their problem in detail. What should you do?",
                "options": [
                    "Interrupt them to save time and suggest a treatment",
                    "Let them talk without interrupting, they are building emotional investment",
                    "Redirect them to talk about pricing",
                    "Put them on hold to check with the doctor"
                ],
                "correct_answer": 1,
                "explanation": "When the patient talks about their problem, they convince themselves they need a solution. Every word they speak increases emotional investment. Never interrupt during discovery."
            },
            {
                "id": "q4",
                "question": "What is the purpose of the question 'What made you inquire?'",
                "options": [
                    "To find out which ad they clicked",
                    "To understand the trigger event that motivated them to seek help now",
                    "To check their marketing attribution",
                    "To see how much they know about treatments"
                ],
                "correct_answer": 1,
                "explanation": "This question uncovers the trigger, the specific event or feeling that pushed the patient to take action now. Understanding this helps you frame your recommendation around their urgency."
            }
        ],
        "mock_scenarios": [
            {
                "id": "mock_02_01",
                "title": "Acne Patient Discovery",
                "patient_profile": "Sneha, 22, college student, inquired about acne treatment",
                "patient_personality": "Emotional about her skin, has tried multiple products, frustrated",
                "opening_context": "She sounds a bit low on confidence when she picks up",
                "evaluation_criteria": ["Asked what concerns she is facing", "Asked what made her inquire now", "Asked about desired results", "Did not pitch treatment during discovery", "Let her speak without interrupting"]
            }
        ]
    },
    {
        "id": "mod_03_mini_diagnosis",
        "order": 3,
        "title": "Phase 3: Mini Diagnosis",
        "subtitle": "Understand the History Before Recommending",
        "description": "Learn to ask diagnostic questions that reveal the patient's history, past failures, and expectation level. This phase separates amateur staff from professionals.",
        "duration_minutes": 20,
        "category": "5_phase_framework",
        "icon": "stethoscope",
        "color": "#8B5CF6",
        "learning_objectives": [
            "Ask history questions: How long, what tried, who consulted",
            "Understand patient awareness level (first timer vs experienced)",
            "Identify past treatment failures and why they failed",
            "Set realistic expectation levels based on history",
            "Use diagnosis information to strengthen your later recommendation"
        ],
        "key_concepts": [
            {
                "title": "The Three Diagnosis Questions",
                "content": "Every mini diagnosis should cover: (1) How long have you had this issue? (2) Have you tried treatments before? (3) Did you consult any doctor? These three questions reveal everything you need to know about the patient's history."
            },
            {
                "title": "What Diagnosis Reveals",
                "content": "These questions help you understand three critical things: Patient awareness (how much they know about their condition), Past failures (what didn't work and why, which you can address in your recommendation), and Expectation level (are they realistic or do they need expectation management)."
            },
            {
                "title": "Diagnosis Strengthens Your Recommendation",
                "content": "When you know what the patient tried before and why it failed, you can position your treatment as the solution to their specific failed attempts. 'I understand you tried topical treatments for 2 years. The reason they didn't work is... Our approach is different because...' This is infinitely more persuasive than a generic pitch."
            }
        ],
        "common_mistakes": [
            "Skipping diagnosis entirely and going straight from discovery to recommendation",
            "Asking diagnosis questions but not listening to the answers",
            "Not using the diagnosis information later when making the recommendation",
            "Making the patient feel judged for past treatment choices",
            "Rushing through diagnosis because you already know what to recommend"
        ],
        "practice_exercises": [
            {
                "type": "script_practice",
                "title": "Diagnosis Deep Dive",
                "instruction": "A patient named Meera says she has pigmentation on her cheeks. Write 4 diagnosis questions to understand her full history.",
                "sample_answer": "1. 'How long have you been dealing with this pigmentation, Meera?' 2. 'Have you tried any treatments or products for it before?' 3. 'If you tried something, what happened? Did it improve or come back?' 4. 'Did you consult a dermatologist about this, or is this your first time exploring professional treatment?'"
            }
        ],
        "quiz": [
            {
                "id": "q1",
                "question": "What are the three core mini diagnosis questions?",
                "options": [
                    "What is your budget? When can you come? Which treatment?",
                    "How long have you had this issue? Tried treatments before? Consulted a doctor?",
                    "What is your age? Your skin type? Your medical history?",
                    "Are you married? Working? Living nearby?"
                ],
                "correct_answer": 1,
                "explanation": "The SBA Mini Diagnosis uses: How long have you had this issue? Have you tried treatments before? Did you consult any doctor? These reveal patient awareness, past failures, and expectation level."
            },
            {
                "id": "q2",
                "question": "Why is knowing about past treatment failures valuable?",
                "options": [
                    "So you can criticize the previous clinic",
                    "So you can position your treatment as the solution to their specific failed attempts",
                    "So you can charge them more",
                    "It has no real value"
                ],
                "correct_answer": 1,
                "explanation": "When you know what failed before and why, you can position your treatment as specifically addressing those failures. This is far more persuasive than a generic recommendation."
            },
            {
                "id": "q3",
                "question": "What three things does the mini diagnosis reveal about the patient?",
                "options": [
                    "Budget, timeline, preference",
                    "Patient awareness, past failures, expectation level",
                    "Age, location, insurance",
                    "Treatment type, number of sessions, recovery time"
                ],
                "correct_answer": 1,
                "explanation": "Mini diagnosis reveals patient awareness (how much they know), past failures (what didn't work), and expectation level (realistic or needs management). This information is critical for Phase 5."
            }
        ],
        "mock_scenarios": [
            {
                "id": "mock_03_01",
                "title": "Repeat Treatment Seeker",
                "patient_profile": "Karan, 35, tried PRP at another clinic 6 months ago with no results, now asking about hair transplant",
                "patient_personality": "Skeptical, has trust issues with clinics, needs reassurance",
                "opening_context": "He sounds guarded and mentions upfront that he wasted money at another clinic",
                "evaluation_criteria": ["Asked how long he has had hair loss", "Asked about previous PRP experience in detail", "Asked why he thinks it didn't work", "Did not criticize the previous clinic", "Used his history to transition naturally"]
            }
        ]
    },
    {
        "id": "mod_04_emotional_impact",
        "order": 4,
        "title": "Phase 4: Emotional Impact",
        "subtitle": "The Phase That Makes Patients Book",
        "description": "Master the most powerful phase in the SBA framework. Learn how emotional impact questions create natural urgency and drive patients to take action without being pushy.",
        "duration_minutes": 25,
        "category": "5_phase_framework",
        "icon": "heart",
        "color": "#EF4444",
        "learning_objectives": [
            "Understand why patients buy emotionally, not logically",
            "Ask emotional impact questions that create natural urgency",
            "Connect the patient's problem to their daily life, confidence, and social situations",
            "Create urgency without being pushy or manipulative",
            "Use emotional impact to naturally transition to recommendation"
        ],
        "key_concepts": [
            {
                "title": "Patients Buy Emotionally",
                "content": "This phase is crucial. Patients buy emotionally, not logically. A patient who understands their problem logically may still not book. But a patient who FEELS the impact of their problem on their life will take action. Your job is to help them feel what they already know."
            },
            {
                "title": "The Emotional Impact Questions",
                "content": "These questions connect the clinical problem to the patient's daily life: 'Does this affect your confidence?', 'Do you avoid photos because of this?', 'Has this affected your social life?', 'Do you feel conscious about this when meeting people?', 'Has this stopped you from doing something you enjoy?' These are not manipulative. They help the patient articulate what they already feel."
            },
            {
                "title": "Natural Urgency vs Pushy Urgency",
                "content": "Pushy urgency: 'We have only 2 slots left this week, you must book now!' Natural urgency: 'You mentioned this has been affecting your confidence for 3 years. Every month you wait is another month of that feeling. Do you think it's time to address this properly?' The second creates urgency from the patient's own words and feelings."
            }
        ],
        "common_mistakes": [
            "Skipping emotional impact entirely and going straight to recommendation",
            "Using artificial urgency tactics (fake limited slots, fake discounts ending today)",
            "Asking emotional questions in a mechanical, checklist way",
            "Not pausing after asking an emotional question to let the patient reflect",
            "Feeling uncomfortable asking emotional questions and rushing past them"
        ],
        "practice_exercises": [
            {
                "type": "script_practice",
                "title": "Emotional Impact Questions",
                "instruction": "A patient named Deepa has been dealing with severe acne scars for 5 years. She has tried creams and facials with no results. Write 3 emotional impact questions.",
                "sample_answer": "1. 'Deepa, you mentioned living with these scars for 5 years. Does it affect how you feel when you look in the mirror?' 2. 'Do you find yourself avoiding photos or social events because of this?' 3. 'If this could be significantly improved, how do you think that would change things for you?'"
            }
        ],
        "quiz": [
            {
                "id": "q1",
                "question": "Why is Phase 4 (Emotional Impact) considered the most powerful phase?",
                "options": [
                    "Because it's where you offer discounts",
                    "Because patients buy emotionally, and this phase connects the problem to their feelings and daily life",
                    "Because it's where you close the sale",
                    "Because it's the longest phase"
                ],
                "correct_answer": 1,
                "explanation": "Patients buy emotionally. A patient who logically understands their problem may not book. But a patient who feels the impact on their confidence, social life, and daily experience will take action."
            },
            {
                "id": "q2",
                "question": "Which is an example of natural urgency vs pushy urgency?",
                "options": [
                    "'Only 2 slots left this week!' is natural urgency",
                    "'You mentioned this has affected your confidence for 3 years. Every month you wait is another month of that feeling.' is natural urgency",
                    "Both are equally effective",
                    "Neither creates urgency"
                ],
                "correct_answer": 1,
                "explanation": "Natural urgency comes from the patient's own words and feelings. Pushy urgency uses artificial scarcity. Natural urgency is far more effective and builds trust rather than pressure."
            },
            {
                "id": "q3",
                "question": "After asking an emotional impact question, what should you do?",
                "options": [
                    "Immediately follow up with another question",
                    "Start recommending a treatment",
                    "Pause and let the patient reflect and respond fully",
                    "Fill the silence by talking about the clinic"
                ],
                "correct_answer": 2,
                "explanation": "After asking an emotional question, pause. Let the patient sit with the feeling and respond. Silence after an emotional question is powerful. The patient will often share much deeper feelings if you give them space."
            }
        ],
        "mock_scenarios": [
            {
                "id": "mock_04_01",
                "title": "Confidence and Social Impact",
                "patient_profile": "Arjun, 30, has dark circles and pigmentation, works in sales and meets clients daily",
                "patient_personality": "Aware of the problem but hasn't connected it to his daily confidence. Needs gentle guidance.",
                "opening_context": "He mentioned during discovery that he has been using concealers before meetings",
                "evaluation_criteria": ["Asked about impact on confidence", "Connected problem to his professional life", "Asked about daily coping mechanisms", "Did not rush past emotional responses", "Created natural urgency without being pushy"]
            }
        ]
    },
    {
        "id": "mod_05_recommendation_close",
        "order": 5,
        "title": "Phase 5: Recommendation + Appointment",
        "subtitle": "Close With Confidence, Not Pressure",
        "description": "Learn the SBA closing methodology: repeat the problem, explain why past treatments failed, recommend the right solution, and use the soft close technique to book consultations.",
        "duration_minutes": 25,
        "category": "5_phase_framework",
        "icon": "calendar-check",
        "color": "#F59E0B",
        "learning_objectives": [
            "Follow the recommendation structure: Repeat problem > Explain past failure > Recommend solution > Introduce treatment",
            "Master the soft close technique",
            "Never pitch treatments before completing Phases 1-4",
            "Create a clear path from recommendation to appointment booking",
            "Handle the transition from conversation to scheduling naturally"
        ],
        "key_concepts": [
            {
                "title": "The Recommendation Structure",
                "content": "Never just say 'We recommend treatment X.' Follow this structure: (1) Repeat the patient's problem in their own words, (2) Explain why their previous treatment failed (using diagnosis info), (3) Recommend the right solution and why it's different, (4) Only then introduce the specific treatment. This makes your recommendation feel like a personalized solution, not a sales pitch."
            },
            {
                "title": "The Soft Close",
                "content": "The SBA soft close has two steps. First: 'Do you think expert consultation could help you with this?' This gets a conceptual yes. Second: 'Should I book you for 6 PM today or would tomorrow morning work better?' This assumes the booking and gives a choice of times, not a choice of yes/no."
            },
            {
                "title": "Why Phases 1-4 Make Closing Easy",
                "content": "If you have done Opening, Discovery, Mini Diagnosis, and Emotional Impact correctly, the patient is already 80% ready to book. They feel heard, they understand their problem deeply, they feel the emotional urgency. Your recommendation is just the logical next step. Closing should feel natural, not forced."
            }
        ],
        "common_mistakes": [
            "Pitching the treatment before completing discovery and emotional impact",
            "Giving a generic recommendation that doesn't reference the patient's specific situation",
            "Asking 'Would you like to book?' (gives yes/no option) instead of 'When works better for you?'",
            "Forgetting to use the patient's own words when summarizing their problem",
            "Not handling the transition from recommendation to booking, leaving it open-ended"
        ],
        "practice_exercises": [
            {
                "type": "script_practice",
                "title": "Full Recommendation Script",
                "instruction": "Patient Anita has had acne scars for 4 years, tried chemical peels at another clinic that faded but came back, and it affects her confidence at work events. Write a full recommendation using the SBA structure.",
                "sample_answer": "Anita, from what you've shared, you've been dealing with these acne scars for 4 years, and it's been affecting your confidence, especially at work events. The chemical peels you tried helped temporarily but the scars returned because peels only work on the surface. What you need is a treatment that works deeper on the skin layers to stimulate collagen from within. Our fractional laser treatment does exactly that, and it's specifically designed for stubborn scars like yours. Do you think it would help to consult with our dermatologist who can examine your skin and create a personalized plan? Great, would 5 PM today work, or is tomorrow evening better?"
            }
        ],
        "quiz": [
            {
                "id": "q1",
                "question": "What is the correct recommendation structure?",
                "options": [
                    "Treatment name > Price > Booking",
                    "Repeat patient problem > Explain past failure > Recommend solution > Introduce treatment",
                    "List all treatments > Let patient choose > Book",
                    "Offer discount > Create urgency > Book immediately"
                ],
                "correct_answer": 1,
                "explanation": "The SBA structure ensures your recommendation feels personalized: repeat their problem in their words, explain why past treatment failed, recommend the right solution, then introduce the specific treatment."
            },
            {
                "id": "q2",
                "question": "What is the SBA soft close technique?",
                "options": [
                    "Ask 'Would you like to book an appointment?'",
                    "First ask 'Do you think expert consultation could help?' then 'Should I book you for 6 PM today?'",
                    "Say 'We have limited slots, you should book now.'",
                    "Send a WhatsApp link and wait"
                ],
                "correct_answer": 1,
                "explanation": "The soft close first gets a conceptual yes ('Do you think expert consultation could help?'), then assumes the booking with a choice of times ('Should I book you for 6 PM or tomorrow morning?'), not a yes/no choice."
            }
        ],
        "mock_scenarios": [
            {
                "id": "mock_05_01",
                "title": "Full Phase 5 Close",
                "patient_profile": "Sanjay, 42, receding hairline for 8 years, tried minoxidil and PRP with limited results, it's affecting his confidence at board meetings",
                "patient_personality": "Ready to commit but needs reassurance. Wants to feel like this is the right decision.",
                "opening_context": "You have completed Phases 1-4 successfully. Now transition to recommendation and close.",
                "evaluation_criteria": ["Repeated his problem in his own words", "Referenced why minoxidil and PRP had limited results", "Recommended specific approach and why it's different", "Used soft close technique", "Gave choice of appointment times, not yes/no"]
            }
        ]
    },
    {
        "id": "mod_06_objection_handling",
        "order": 6,
        "title": "AAA Objection Handling",
        "subtitle": "Agree, Associate, Ask",
        "description": "Master the SBA's proprietary AAA Framework for handling every type of patient objection: price, distance, timing, doubt, and fear. Learn why arguing with patients kills deals.",
        "duration_minutes": 30,
        "category": "advanced_skills",
        "icon": "shield",
        "color": "#EC4899",
        "learning_objectives": [
            "Apply the AAA Framework: Agree > Associate > Ask",
            "Handle price objections without discounting",
            "Handle distance and timing objections",
            "Handle doubt and fear objections with social proof",
            "Never argue with a patient, even when they are wrong"
        ],
        "key_concepts": [
            {
                "title": "The AAA Framework",
                "content": "When patients raise objections, never argue. Follow three steps: (1) AGREE: Validate the concern. 'I understand it may feel expensive.' (2) ASSOCIATE: Use social proof or a story. 'One of our patients had the same concern.' (3) ASK: Ask a question with an obvious answer. 'If this treatment solves your problem, do you think it would be worth it?'"
            },
            {
                "title": "Price Objection Handling",
                "content": "Price is the most common objection. The mistake is to immediately offer a discount. Instead: Agree: 'I completely understand, it's an investment.' Associate: 'Many of our patients felt the same way initially. One patient told us she spent more on products that didn't work over 3 years than the entire treatment cost.' Ask: 'If this treatment actually solves the problem you've been dealing with for X years, do you think it would be worth the investment?'"
            },
            {
                "title": "Distance Objection Handling",
                "content": "Agree: 'You're right, we're not the closest option.' Associate: 'We have many patients who travel from even further because they want the right expertise for their specific condition.' Ask: 'Would you rather save 30 minutes of travel or get the treatment done right the first time?'"
            },
            {
                "title": "Why Never Argue",
                "content": "The moment you argue with a patient's objection, you put them in a defensive position. They will dig in harder. Agreeing first disarms them. They expected pushback and didn't get it. This opens their mind to hearing your perspective through the Associate and Ask steps."
            }
        ],
        "common_mistakes": [
            "Immediately defending the clinic when a patient raises a concern",
            "Offering discounts as the first response to price objections",
            "Dismissing the objection: 'Oh that's not a problem'",
            "Getting emotional or frustrated when patients push back",
            "Not having social proof stories ready for common objections",
            "Forgetting to end with a question (the Ask step)"
        ],
        "practice_exercises": [
            {
                "type": "script_practice",
                "title": "Handle These Objections",
                "instruction": "Write AAA responses for each objection: (1) 'That's too expensive.' (2) 'Your clinic is too far.' (3) 'I need to think about it.'",
                "sample_answer": "Price: Agree: 'I understand, it's definitely an investment.' Associate: 'One of our patients spent over 50,000 on products over 5 years that didn't work. The treatment cost was actually less than that.' Ask: 'If this solves a problem you've had for years, would it be worth the investment?' | Distance: Agree: 'You're right, we're not the closest option.' Associate: 'We have patients who travel from across the city because the results matter more to them than convenience.' Ask: 'Would you rather save travel time or get the treatment done right?' | Think about it: Agree: 'Of course, this is an important decision.' Associate: 'Most of our patients wanted to think about it too. What we found is that a quick consultation helped them make a confident decision.' Ask: 'Would it help to just come in for a consultation so you have all the information you need to decide?'"
            }
        ],
        "quiz": [
            {
                "id": "q1",
                "question": "What does AAA stand for in the SBA Objection Handling Framework?",
                "options": [
                    "Answer, Argue, Advance",
                    "Agree, Associate, Ask",
                    "Accept, Adapt, Act",
                    "Acknowledge, Address, Affirm"
                ],
                "correct_answer": 1,
                "explanation": "AAA stands for Agree (validate), Associate (social proof), Ask (question with obvious answer). This structure disarms objections without arguing."
            },
            {
                "id": "q2",
                "question": "A patient says 'Rs 30,000 is too much.' What is the WORST first response?",
                "options": [
                    "'I understand it feels like a big investment.'",
                    "'We can offer you a 20% discount.'",
                    "'Many patients felt the same way initially.'",
                    "'If this solves your 5-year problem, would it be worth it?'"
                ],
                "correct_answer": 1,
                "explanation": "Immediately offering a discount devalues your service and trains patients to always negotiate. The AAA approach validates first, shares social proof, then reframes the value through a question."
            },
            {
                "id": "q3",
                "question": "Why should you NEVER argue with a patient's objection?",
                "options": [
                    "Because the patient is always right",
                    "Because arguing puts them in a defensive position where they dig in harder",
                    "Because it wastes time",
                    "Because your manager will be upset"
                ],
                "correct_answer": 1,
                "explanation": "Arguing triggers a defensive reaction. The patient digs in harder. Agreeing first disarms them because they expected pushback. This opens their mind to the Associate and Ask steps."
            }
        ],
        "mock_scenarios": [
            {
                "id": "mock_06_01",
                "title": "Price Objection Drill",
                "patient_profile": "Neha, 28, wants skin brightening treatment. After learning the price is Rs 25,000, she says it's too expensive.",
                "patient_personality": "Has been comparing prices online, expects a discount, not fully sold on the value yet",
                "opening_context": "You've completed Phases 1-4. She was interested but the price created hesitation.",
                "evaluation_criteria": ["Did not immediately offer a discount", "Used Agree step to validate", "Shared a relevant social proof story", "Asked a reframing question", "Maintained warmth and composure"]
            },
            {
                "id": "mock_06_02",
                "title": "Multiple Objections",
                "patient_profile": "Raj, 45, interested in hair transplant but says 'It's expensive, your clinic is far, and I need to discuss with my wife.'",
                "patient_personality": "Actually interested but using objections as a safety net. Needs patient handling.",
                "opening_context": "He raised all three objections back to back after hearing the treatment recommendation.",
                "evaluation_criteria": ["Addressed each objection separately using AAA", "Did not get overwhelmed by multiple objections", "Identified the real objection (likely fear/doubt, not all three)", "Used social proof for the most important objection", "Ended with a clear next step"]
            }
        ]
    },
    {
        "id": "mod_07_call_control",
        "order": 7,
        "title": "Call Control & Mirroring",
        "subtitle": "Own the Conversation Flow",
        "description": "Learn the two most powerful micro-skills in the SBA system: call control through strategic questioning and the mirroring technique that makes patients feel deeply heard.",
        "duration_minutes": 20,
        "category": "advanced_skills",
        "icon": "mic",
        "color": "#6366F1",
        "learning_objectives": [
            "Understand that whoever asks questions controls the conversation",
            "Regain control when the patient takes over with questions",
            "Master the mirroring technique for instant rapport",
            "Combine call control with mirroring for maximum effectiveness",
            "Handle rapid-fire patient questions without losing control"
        ],
        "key_concepts": [
            {
                "title": "Questions Equal Control",
                "content": "Whoever asks questions controls the conversation. If the patient asks about price, location, or doctor experience, the patient controls the call. If staff asks problem questions, diagnosis questions, and emotional questions, staff controls the call. The rule: whenever a patient asks a question, answer them briefly and end the answer with a follow-up question to get control back."
            },
            {
                "title": "The Control Recovery Technique",
                "content": "Patient asks: 'What is the price?' Instead of just answering the price, respond: 'It depends on your specific condition and the treatment plan the doctor recommends. Can I ask how long you have been dealing with this issue?' You answered their question and immediately regained control with a question of your own."
            },
            {
                "title": "The Mirroring Technique",
                "content": "Repeat the patient's key words back to them. This makes them feel deeply heard and encourages them to share more. Patient: 'I've had acne for 3 years.' You: '3 years?' Then pause. The patient will almost always elaborate with more detail. Then ask your follow-up question. Mirroring builds rapport faster than any other technique."
            },
            {
                "title": "Combining Control + Mirroring",
                "content": "Patient asks: 'Is your treatment expensive?' You: 'Expensive?' (mirror) Patient: 'Yes, I've been quoted 50,000 elsewhere.' You: '50,000, I see. What treatments were included in that quote?' (regain control). You mirrored twice and regained control with a question, all while making the patient feel heard."
            }
        ],
        "common_mistakes": [
            "Answering patient questions fully and then waiting for the next question (losing control)",
            "Not ending answers with follow-up questions",
            "Mirroring too much (feels like mocking if overdone)",
            "Mirroring with a sarcastic or questioning tone instead of empathetic curiosity",
            "Panicking when the patient asks rapid-fire questions and just answering all of them"
        ],
        "practice_exercises": [
            {
                "type": "script_practice",
                "title": "Regain Control",
                "instruction": "Write control recovery responses for these patient questions: (1) 'How much does hair transplant cost?' (2) 'Is your doctor experienced?' (3) 'Do you have a branch near Andheri?'",
                "sample_answer": "Price: 'The cost depends on the number of grafts you need, which is based on your specific hair loss pattern. Can I ask when you first started noticing the thinning?' Doctor: 'Our doctor has over 15 years of experience and has done over 5,000 procedures. Can I know a bit about your situation so I can explain what approach would work best for you?' Location: 'Our main clinic is at [location] which is designed specifically for these procedures with the latest equipment. May I ask what area of hair loss concerns you most?'"
            }
        ],
        "quiz": [
            {
                "id": "q1",
                "question": "A patient asks 'What is the price of PRP?' What is the best response?",
                "options": [
                    "'PRP costs Rs 8,000 per session.'",
                    "'It depends on your condition. Can I ask how long you've been dealing with hair loss?'",
                    "'Why are you asking about price first?'",
                    "'We have the best prices in the market.'"
                ],
                "correct_answer": 1,
                "explanation": "Answer briefly (it depends on condition) then regain control with a discovery question. This keeps you in control while also addressing their concern."
            },
            {
                "id": "q2",
                "question": "What is the mirroring technique?",
                "options": [
                    "Copying the patient's tone of voice exactly",
                    "Repeating the patient's key words back to them to make them feel heard and encourage elaboration",
                    "Sending them a mirror image of their treatment options",
                    "Reflecting on the call after it ends"
                ],
                "correct_answer": 1,
                "explanation": "Mirroring means repeating the patient's key words. Patient: 'I've had acne for 3 years.' You: '3 years?' Then pause. The patient elaborates. This builds rapport faster than any other technique."
            }
        ],
        "mock_scenarios": [
            {
                "id": "mock_07_01",
                "title": "Rapid Fire Questions",
                "patient_profile": "Arun, 38, fires off questions: 'What is the cost? How many sessions? Is it painful? How long is recovery? Do you have EMI?'",
                "patient_personality": "Research-oriented, wants answers fast, but if you just answer everything he'll compare you as a commodity",
                "opening_context": "He started asking questions within the first 30 seconds of the call",
                "evaluation_criteria": ["Did not answer all questions in sequence", "Answered one question briefly then regained control", "Used mirroring to slow the pace", "Transitioned into discovery", "Maintained calm and confident tone"]
            }
        ]
    },
    {
        "id": "mod_08_follow_up",
        "order": 8,
        "title": "Follow-Up SOP & Persistence",
        "subtitle": "The Fortune is in the Follow-Up",
        "description": "Master the SBA follow-up cadence that converts leads who didn't book on the first call. Learn the exact timing, messaging, and WhatsApp strategy.",
        "duration_minutes": 15,
        "category": "systems",
        "icon": "phone-forwarded",
        "color": "#14B8A6",
        "learning_objectives": [
            "Follow the SBA 4-step follow-up cadence",
            "Understand why most conversions happen after the first call",
            "Use WhatsApp effectively as a follow-up channel",
            "Know when to move a lead from follow-up to nurture",
            "Track follow-up consistency and its impact on conversion"
        ],
        "key_concepts": [
            {
                "title": "The SBA Follow-Up Cadence",
                "content": "Not all leads convert on the first call. The follow-up rule: 1st call: immediately after the lead comes in. 2nd call: same day evening. 3rd call: next day. 4th follow-up: WhatsApp message. Maximum attempts: 3-4 calls before moving to nurture. Most clinics lose leads because they give up after one call."
            },
            {
                "title": "Speed to Lead",
                "content": "The first call must happen immediately. Studies show that leads contacted within 5 minutes are 10x more likely to convert than leads contacted after 30 minutes. The lead is most interested the moment they fill the form or make the inquiry."
            },
            {
                "title": "WhatsApp as the 4th Touch",
                "content": "If the patient hasn't responded to 3 calls, switch to WhatsApp. Keep it personal, not salesy. Example: 'Hi Priya, this is Meenu from Dr K's Clinic. You had inquired about laser treatment. I tried calling a couple of times. Would it be easier to chat here? Happy to answer any questions.' This gives the patient a low-pressure way to engage."
            }
        ],
        "common_mistakes": [
            "Only calling once and giving up if the patient doesn't answer",
            "Waiting hours or days to make the first follow-up call",
            "Calling at random times instead of following the cadence",
            "Sending generic WhatsApp messages that feel like mass marketing",
            "Not tracking follow-up attempts per lead"
        ],
        "practice_exercises": [
            {
                "type": "script_practice",
                "title": "WhatsApp Follow-Up Message",
                "instruction": "Write a WhatsApp follow-up message for a lead named Rohit who inquired about teeth whitening but hasn't answered 3 calls.",
                "sample_answer": "Hi Rohit, this is [Name] from [Clinic]. You had inquired about teeth whitening. I tried reaching you by phone a couple of times. Would it be easier to chat here? I am happy to answer any questions or help you book a quick consultation. No pressure at all."
            }
        ],
        "quiz": [
            {
                "id": "q1",
                "question": "What is the correct SBA follow-up cadence?",
                "options": [
                    "Call once, then email after a week",
                    "1st call immediately, 2nd same day evening, 3rd next day, 4th WhatsApp",
                    "Send WhatsApp first, then call if they reply",
                    "Call three times in a row on the same day"
                ],
                "correct_answer": 1,
                "explanation": "The SBA cadence is: 1st call immediately, 2nd same day evening, 3rd next day, 4th WhatsApp. This gives the patient multiple touch points without being aggressive."
            },
            {
                "id": "q2",
                "question": "Why is the FIRST follow-up call timing critical?",
                "options": [
                    "Because the clinic is less busy in the morning",
                    "Because leads contacted within 5 minutes are 10x more likely to convert",
                    "Because it impresses the patient",
                    "Because competitors might call first"
                ],
                "correct_answer": 1,
                "explanation": "Speed to lead matters enormously. Leads contacted within 5 minutes of their inquiry are 10x more likely to convert. The lead is most interested the moment they reach out."
            }
        ],
        "mock_scenarios": [
            {
                "id": "mock_08_01",
                "title": "Second Call Follow-Up",
                "patient_profile": "Pooja, 31, inquired about skin treatment in the morning, first call went to voicemail. Now calling in the evening.",
                "patient_personality": "Busy, appreciates efficiency, doesn't want to repeat herself",
                "opening_context": "This is the 2nd call per the SBA cadence. She picks up this time.",
                "evaluation_criteria": ["Acknowledged this is a follow-up attempt", "Used her name", "Referenced her specific inquiry", "Did not make her feel bad for missing the first call", "Smoothly transitioned into discovery"]
            }
        ]
    }
]


# ---- CERTIFICATION REQUIREMENTS ----

CERTIFICATION_LEVELS = [
    {
        "id": "cert_foundation",
        "title": "SBA Foundation Certified",
        "description": "Completed all 8 core modules with passing scores",
        "requirements": {
            "modules_completed": ["mod_01_opening", "mod_02_problem_discovery", "mod_03_mini_diagnosis", "mod_04_emotional_impact", "mod_05_recommendation_close", "mod_06_objection_handling", "mod_07_call_control", "mod_08_follow_up"],
            "min_quiz_score": 75,
            "min_mock_score": 70
        },
        "badge_color": "#3B82F6",
        "badge_icon": "award"
    },
    {
        "id": "cert_advanced",
        "title": "SBA Advanced Practitioner",
        "description": "Foundation certified + 90% quiz scores + 85% mock scores + 30 real calls scored above 70",
        "requirements": {
            "prerequisite": "cert_foundation",
            "min_quiz_score": 90,
            "min_mock_score": 85,
            "real_calls_above_70": 30
        },
        "badge_color": "#F59E0B",
        "badge_icon": "trophy"
    },
    {
        "id": "cert_master",
        "title": "SBA Master Coach",
        "description": "Advanced certified + 95% quiz scores + 90% mock scores + 100 real calls scored above 80 + consistently in top 3 leaderboard",
        "requirements": {
            "prerequisite": "cert_advanced",
            "min_quiz_score": 95,
            "min_mock_score": 90,
            "real_calls_above_80": 100,
            "leaderboard_top_3_weeks": 4
        },
        "badge_color": "#EF4444",
        "badge_icon": "crown"
    }
]


# ---- HELPER FUNCTIONS ----

def get_all_modules():
    """Return all learning modules."""
    return LEARNING_MODULES


def get_module_by_id(module_id: str):
    """Return a specific module by ID."""
    for mod in LEARNING_MODULES:
        if mod["id"] == module_id:
            return mod
    return None


def get_modules_by_category(category: str):
    """Return modules filtered by category."""
    return [m for m in LEARNING_MODULES if m["category"] == category]


def get_quiz_for_module(module_id: str):
    """Return quiz questions for a specific module."""
    mod = get_module_by_id(module_id)
    if mod:
        return mod.get("quiz", [])
    return []


def get_mock_scenarios_for_module(module_id: str):
    """Return mock call scenarios for a specific module."""
    mod = get_module_by_id(module_id)
    if mod:
        return mod.get("mock_scenarios", [])
    return []


def grade_quiz(module_id: str, answers: dict) -> dict:
    """Grade a quiz submission and return results.

    Args:
        module_id: The module ID
        answers: Dict mapping question_id to selected_answer_index (0-based)

    Returns:
        Dict with score, total, percentage, and per-question results
    """
    quiz = get_quiz_for_module(module_id)
    if not quiz:
        return {"error": "Module or quiz not found"}

    results = []
    correct_count = 0

    for q in quiz:
        user_answer = answers.get(q["id"])
        is_correct = user_answer == q["correct_answer"]
        if is_correct:
            correct_count += 1
        results.append({
            "question_id": q["id"],
            "question": q["question"],
            "user_answer": user_answer,
            "correct_answer": q["correct_answer"],
            "is_correct": is_correct,
            "explanation": q["explanation"]
        })

    total = len(quiz)
    percentage = round((correct_count / total) * 100) if total > 0 else 0

    return {
        "module_id": module_id,
        "correct": correct_count,
        "total": total,
        "percentage": percentage,
        "passed": percentage >= 75,
        "results": results
    }


def get_certification_levels():
    """Return all certification level definitions."""
    return CERTIFICATION_LEVELS


def check_certification_eligibility(user_progress: dict) -> list:
    """Check which certifications a user is eligible for.

    Args:
        user_progress: Dict with keys like 'completed_modules', 'quiz_scores', 'mock_scores', 'real_call_scores'

    Returns:
        List of certification IDs the user qualifies for
    """
    eligible = []

    completed_modules = set(user_progress.get("completed_modules", []))
    avg_quiz = user_progress.get("avg_quiz_score", 0)
    avg_mock = user_progress.get("avg_mock_score", 0)
    real_calls_70 = user_progress.get("real_calls_above_70", 0)
    real_calls_80 = user_progress.get("real_calls_above_80", 0)
    top_3_weeks = user_progress.get("leaderboard_top_3_weeks", 0)

    # Foundation
    foundation_reqs = CERTIFICATION_LEVELS[0]["requirements"]
    if (set(foundation_reqs["modules_completed"]).issubset(completed_modules)
            and avg_quiz >= foundation_reqs["min_quiz_score"]
            and avg_mock >= foundation_reqs["min_mock_score"]):
        eligible.append("cert_foundation")

    # Advanced
    if "cert_foundation" in eligible:
        adv_reqs = CERTIFICATION_LEVELS[1]["requirements"]
        if (avg_quiz >= adv_reqs["min_quiz_score"]
                and avg_mock >= adv_reqs["min_mock_score"]
                and real_calls_70 >= adv_reqs["real_calls_above_70"]):
            eligible.append("cert_advanced")

    # Master
    if "cert_advanced" in eligible:
        master_reqs = CERTIFICATION_LEVELS[2]["requirements"]
        if (avg_quiz >= master_reqs["min_quiz_score"]
                and avg_mock >= master_reqs["min_mock_score"]
                and real_calls_80 >= master_reqs["real_calls_above_80"]
                and top_3_weeks >= master_reqs["leaderboard_top_3_weeks"]):
            eligible.append("cert_master")

    return eligible
