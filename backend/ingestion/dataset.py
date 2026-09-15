import os
from typing import List, Dict, Any

SAMPLE_MSMARCO_XI_DOCUMENTS = [
    # ── RAG / AI Infrastructure (original core) ──────────────────────────────
    {
        "document_id": "gen_001",
        "text": "Retrieval-Augmented Generation (RAG) integrates vector database retrieval with generative large language models to produce strictly grounded answers. By injecting verified context passages into prompt windows, factual hallucinations are effectively eliminated.",
        "language": "en"
    },
    {
        "document_id": "gen_002",
        "text": "FAISS (Facebook AI Similarity Search) is an open-source library for efficient similarity search and clustering of dense vectors. It supports vector indexing algorithms including IndexFlatIP, IndexIVFFlat, and HNSW for billion-scale vector similarity matching.",
        "language": "en"
    },
    {
        "document_id": "gen_003",
        "text": "BM25 is a probabilistic ranking function used by search engines to estimate the relevance of matching documents to a search query. It computes term frequency (TF) and inverse document frequency (IDF) with document length normalization factors k1 and b.",
        "language": "en"
    },
    {
        "document_id": "gen_004",
        "text": "Reciprocal Rank Fusion (RRF) is an algorithmic method to combine multiple search ranking lists—such as dense vector search and sparse BM25 lexical search—into a unified rank without requiring score calibration or threshold normalization.",
        "language": "en"
    },
    {
        "document_id": "gen_005",
        "text": "Large Language Models (LLMs) such as GPT-4, Gemini, and Claude are transformer-based neural networks trained on vast corpora of text. They generate human-like text completions, answer questions, write code, and summarize documents with high fluency.",
        "language": "en"
    },
    {
        "document_id": "gen_006",
        "text": "Vector embeddings represent unstructured textual data as high-dimensional numerical vectors. Models such as sentence-transformers capture semantic relationships, synonyms, and contextual meaning across sentences.",
        "language": "en"
    },
    {
        "document_id": "gen_007",
        "text": "FastAPI is a modern, high-performance web framework for building APIs with Python 3.8+ based on standard Python type hints and asynchronous ASGI architecture.",
        "language": "en"
    },
    {
        "document_id": "gen_008",
        "text": "Machine learning is a subset of artificial intelligence where algorithms learn patterns from data to make predictions or decisions without being explicitly programmed. Supervised, unsupervised, and reinforcement learning are the three main paradigms.",
        "language": "en"
    },
    {
        "document_id": "gen_009",
        "text": "Deep learning uses artificial neural networks with many layers (hence 'deep') to automatically learn hierarchical feature representations from raw data like images, audio, or text.",
        "language": "en"
    },
    {
        "document_id": "gen_010",
        "text": "Natural Language Processing (NLP) is the branch of AI concerned with enabling computers to understand, interpret, and generate human language. Key tasks include sentiment analysis, named entity recognition, machine translation, and question answering.",
        "language": "en"
    },

    # ── Science & Physics ─────────────────────────────────────────────────────
    {
        "document_id": "sci_001",
        "text": "The speed of light in a vacuum is approximately 299,792,458 metres per second (about 3×10⁸ m/s). According to Einstein's special theory of relativity, no object with mass can reach or exceed this speed.",
        "language": "en"
    },
    {
        "document_id": "sci_002",
        "text": "Photosynthesis is the biological process by which green plants, algae, and some bacteria convert sunlight, carbon dioxide, and water into glucose and oxygen using chlorophyll pigments.",
        "language": "en"
    },
    {
        "document_id": "sci_003",
        "text": "DNA (deoxyribonucleic acid) is the molecule that carries the genetic instructions for the development, functioning, growth, and reproduction of all known living organisms and many viruses. It consists of two complementary strands forming a double helix.",
        "language": "en"
    },
    {
        "document_id": "sci_004",
        "text": "The Big Bang theory states that the universe began approximately 13.8 billion years ago from an extremely hot and dense singularity, and has been expanding ever since.",
        "language": "en"
    },
    {
        "document_id": "sci_005",
        "text": "Newton's three laws of motion describe the relationship between forces and the motion of objects. The first law states objects remain at rest or in uniform motion unless acted upon by an external force (inertia).",
        "language": "en"
    },
    {
        "document_id": "sci_006",
        "text": "The periodic table organises all known chemical elements in order of increasing atomic number. Elements in the same column (group) share similar chemical properties. There are 118 confirmed elements.",
        "language": "en"
    },
    {
        "document_id": "sci_007",
        "text": "Quantum mechanics is the fundamental theory of physics describing the behaviour of particles at atomic and subatomic scales. It introduces concepts such as wave-particle duality, superposition, and the uncertainty principle.",
        "language": "en"
    },
    {
        "document_id": "sci_008",
        "text": "Evolution by natural selection, proposed by Charles Darwin in 1859, explains how populations of organisms change over successive generations through the differential survival and reproduction of individuals with advantageous traits.",
        "language": "en"
    },
    {
        "document_id": "sci_009",
        "text": "The human body contains approximately 37 trillion cells, organised into tissues, organs, and organ systems such as the cardiovascular, respiratory, nervous, and digestive systems.",
        "language": "en"
    },
    {
        "document_id": "sci_010",
        "text": "Climate change refers to long-term shifts in global temperatures and weather patterns. While natural factors contribute, human activities—especially burning fossil fuels—have been the primary driver since the mid-20th century.",
        "language": "en"
    },
    {
        "document_id": "sci_011",
        "text": "Black holes are regions of spacetime where gravity is so strong that nothing—not even light or electromagnetic radiation—can escape once it crosses the event horizon. They form when massive stars collapse at the end of their life cycles.",
        "language": "en"
    },
    {
        "document_id": "sci_012",
        "text": "CRISPR-Cas9 is a revolutionary gene-editing technology that allows scientists to precisely cut and modify DNA sequences in living organisms. It has applications in treating genetic diseases, developing new medicines, and agricultural improvement.",
        "language": "en"
    },
    {
        "document_id": "sci_013",
        "text": "Vaccines work by training the immune system to recognise and combat pathogens without causing disease. They introduce antigens or instructions (like mRNA) that stimulate antibody production and immunological memory.",
        "language": "en"
    },
    {
        "document_id": "sci_014",
        "text": "The water cycle describes the continuous movement of water on, above, and below the surface of Earth through processes of evaporation, condensation, precipitation, infiltration, and runoff.",
        "language": "en"
    },
    {
        "document_id": "sci_015",
        "text": "Gravity is the fundamental force that attracts objects with mass toward one another. On Earth, gravity gives weight to physical objects and causes the ocean tides through lunar and solar gravitational pull.",
        "language": "en"
    },

    # ── Mathematics ───────────────────────────────────────────────────────────
    {
        "document_id": "math_001",
        "text": "The Pythagorean theorem states that in a right-angled triangle, the square of the hypotenuse equals the sum of the squares of the other two sides: a² + b² = c².",
        "language": "en"
    },
    {
        "document_id": "math_002",
        "text": "Pi (π) is an irrational mathematical constant approximately equal to 3.14159. It represents the ratio of a circle's circumference to its diameter and appears throughout mathematics and physics.",
        "language": "en"
    },
    {
        "document_id": "math_003",
        "text": "Calculus is the branch of mathematics dealing with derivatives (rates of change) and integrals (accumulation of quantities). It was independently developed by Isaac Newton and Gottfried Wilhelm Leibniz in the 17th century.",
        "language": "en"
    },
    {
        "document_id": "math_004",
        "text": "Prime numbers are natural numbers greater than 1 that have no positive divisors other than 1 and themselves. Examples include 2, 3, 5, 7, 11, and 13. The number 2 is the only even prime.",
        "language": "en"
    },
    {
        "document_id": "math_005",
        "text": "Statistics is the science of collecting, analysing, interpreting, and presenting data. Key concepts include mean (average), median, standard deviation, probability distributions, and hypothesis testing.",
        "language": "en"
    },

    # ── World History ─────────────────────────────────────────────────────────
    {
        "document_id": "hist_001",
        "text": "World War II (1939–1945) was the deadliest conflict in human history, involving most of the world's nations. It ended with the Allied victory over Nazi Germany and Imperial Japan, leading to the United Nations' formation.",
        "language": "en"
    },
    {
        "document_id": "hist_002",
        "text": "The Renaissance was a cultural and intellectual movement that began in Italy in the 14th century and spread across Europe, marking the transition from the Middle Ages to modernity. It emphasised humanism, science, and the arts.",
        "language": "en"
    },
    {
        "document_id": "hist_003",
        "text": "The Industrial Revolution began in Britain around 1760 and transformed manufacturing from hand production to machine-based processes. It introduced steam power, iron production, and factory systems, fundamentally changing society.",
        "language": "en"
    },
    {
        "document_id": "hist_004",
        "text": "The French Revolution (1789–1799) was a period of radical political and societal transformation in France that overthrew the monarchy and established a republic based on the ideals of liberty, equality, and fraternity.",
        "language": "en"
    },
    {
        "document_id": "hist_005",
        "text": "India gained independence from British colonial rule on 15 August 1947, becoming the world's largest democracy. The independence movement was led by figures including Mahatma Gandhi, Jawaharlal Nehru, and Subhas Chandra Bose.",
        "language": "en"
    },
    {
        "document_id": "hist_006",
        "text": "The Cold War (1947–1991) was a geopolitical rivalry between the United States and the Soviet Union, characterised by ideological competition, proxy wars, the arms race, and the space race, but never direct military conflict between the superpowers.",
        "language": "en"
    },
    {
        "document_id": "hist_007",
        "text": "Ancient Rome was one of history's greatest civilisations, founding a republic in 509 BC that eventually became the Roman Empire. At its peak, it controlled territory across Europe, North Africa, and the Middle East.",
        "language": "en"
    },
    {
        "document_id": "hist_008",
        "text": "The Silk Road was an ancient network of trade routes connecting China and East Asia with Central Asia, South Asia, the Middle East, East Africa, and Southern Europe, facilitating commerce and cultural exchange for centuries.",
        "language": "en"
    },

    # ── World Geography ───────────────────────────────────────────────────────
    {
        "document_id": "geo_001",
        "text": "Mount Everest, located in the Himalayas on the border of Nepal and Tibet, is Earth's highest mountain above sea level at 8,848.86 metres. It was first summited by Edmund Hillary and Tenzing Norgay in 1953.",
        "language": "en"
    },
    {
        "document_id": "geo_002",
        "text": "The Amazon River in South America is the world's largest river by discharge volume of water. The Amazon basin contains the largest tropical rainforest on Earth, covering around 5.5 million square kilometres.",
        "language": "en"
    },
    {
        "document_id": "geo_003",
        "text": "The Sahara Desert in North Africa is the world's largest hot desert, spanning approximately 9.2 million square kilometres across 11 countries. Despite its harsh conditions, it supports diverse life forms.",
        "language": "en"
    },
    {
        "document_id": "geo_004",
        "text": "The Pacific Ocean is the largest and deepest of Earth's five oceans, covering more than 30% of Earth's surface. The Mariana Trench, located in the western Pacific, is the deepest known point on Earth at about 11,034 metres.",
        "language": "en"
    },
    {
        "document_id": "geo_005",
        "text": "India is the seventh-largest country by area and the most populous country in the world. It is located in South Asia and shares borders with Pakistan, China, Nepal, Bhutan, Bangladesh, and Myanmar.",
        "language": "en"
    },
    {
        "document_id": "geo_006",
        "text": "The continent of Africa is the second-largest continent, covering about 30.3 million square kilometres. It is home to 54 recognised countries and extraordinary biodiversity, including the Serengeti ecosystem.",
        "language": "en"
    },
    {
        "document_id": "geo_007",
        "text": "Goa is a coastal state located in Western India along the Arabian Sea. It is India's smallest state by area and is renowned for its rich cultural history, Portuguese colonial architecture, palm-fringed beaches, and vibrant tourism industry.",
        "language": "en"
    },
    {
        "document_id": "geo_008",
        "text": "The Nile River, flowing through northeastern Africa for approximately 6,650 kilometres, is considered the longest river in the world. It has been vital to the civilisations of Egypt and Sudan for millennia.",
        "language": "en"
    },

    # ── Countries & Capitals ──────────────────────────────────────────────────
    {
        "document_id": "cap_001",
        "text": "The capital of France is Paris, which is also the country's largest city. France is located in Western Europe and is known for the Eiffel Tower, the Louvre Museum, and its contributions to art, fashion, and cuisine.",
        "language": "en"
    },
    {
        "document_id": "cap_002",
        "text": "Washington, D.C. is the capital of the United States of America. The city is home to the White House, the US Capitol, the Supreme Court, and numerous national monuments and museums.",
        "language": "en"
    },
    {
        "document_id": "cap_003",
        "text": "New Delhi is the capital of India and serves as the seat of the Indian government. It is distinct from Delhi (the National Capital Territory) and houses Parliament House, Rashtrapati Bhavan, and India Gate.",
        "language": "en"
    },
    {
        "document_id": "cap_004",
        "text": "Beijing is the capital of China and one of the most populous cities in the world. It is home to the Forbidden City, the Great Wall of China, Tiananmen Square, and the Temple of Heaven.",
        "language": "en"
    },
    {
        "document_id": "cap_005",
        "text": "Tokyo is the capital of Japan and the most populous metropolitan area in the world. It is a global centre for finance, technology, and culture, blending ultra-modern architecture with traditional temples.",
        "language": "en"
    },
    {
        "document_id": "cap_006",
        "text": "London is the capital of the United Kingdom and England. It is one of the world's leading financial centres and home to iconic landmarks such as the Tower of London, Buckingham Palace, and the Houses of Parliament.",
        "language": "en"
    },
    {
        "document_id": "cap_007",
        "text": "Moscow is the capital and largest city of Russia. It is the country's political, economic, and cultural centre, featuring landmarks such as the Kremlin, Red Square, and the Bolshoi Theatre.",
        "language": "en"
    },
    {
        "document_id": "cap_008",
        "text": "Canberra is the capital of Australia. It was purpose-built after federation as a compromise between Sydney and Melbourne. The city hosts Parliament House and the Australian War Memorial.",
        "language": "en"
    },
    {
        "document_id": "cap_009",
        "text": "Brasília is the capital of Brazil. Designed by urban planner Lúcio Costa and architect Oscar Niemeyer, it replaced Rio de Janeiro as the capital in 1960 and is a UNESCO World Heritage city.",
        "language": "en"
    },
    {
        "document_id": "cap_010",
        "text": "Berlin is the capital and largest city of Germany. After being divided during the Cold War, the city was reunified in 1990 and has since become a major cultural, political, and economic hub of Europe.",
        "language": "en"
    },

    # ── Health & Medicine ─────────────────────────────────────────────────────
    {
        "document_id": "med_001",
        "text": "The human heart is a muscular organ that pumps blood through the circulatory system. It beats approximately 60–100 times per minute in adults and pumps about 5 litres of blood per minute throughout the body.",
        "language": "en"
    },
    {
        "document_id": "med_002",
        "text": "Diabetes mellitus is a group of metabolic diseases characterised by high blood sugar levels. Type 1 is an autoimmune condition; Type 2 is linked to lifestyle factors. It is managed through diet, exercise, and medication.",
        "language": "en"
    },
    {
        "document_id": "med_003",
        "text": "Antibiotics are medicines that kill or inhibit the growth of bacteria. They are ineffective against viruses. Overuse of antibiotics has led to antibiotic resistance, a major global health threat.",
        "language": "en"
    },
    {
        "document_id": "med_004",
        "text": "The immune system protects the body from pathogens including bacteria, viruses, fungi, and parasites. It consists of white blood cells, antibodies, lymph nodes, the thymus, and the spleen.",
        "language": "en"
    },
    {
        "document_id": "med_005",
        "text": "Sleep is essential for physical and mental health. During sleep, the body repairs tissues, consolidates memories, and regulates hormones. Adults generally require 7–9 hours of sleep per night.",
        "language": "en"
    },
    {
        "document_id": "med_006",
        "text": "Cancer is a group of diseases characterised by the uncontrolled growth and spread of abnormal cells. Treatment options include surgery, chemotherapy, radiation therapy, immunotherapy, and targeted therapy.",
        "language": "en"
    },
    {
        "document_id": "med_007",
        "text": "Mental health encompasses emotional, psychological, and social well-being. Common mental health conditions include depression, anxiety disorders, bipolar disorder, and schizophrenia. Treatment involves therapy, medication, and support.",
        "language": "en"
    },

    # ── Technology & Computing ────────────────────────────────────────────────
    {
        "document_id": "tech_001",
        "text": "The Internet is a global system of interconnected computer networks that use the Internet protocol suite (TCP/IP) to communicate. It was developed from ARPANET in the late 1960s and became publicly accessible in the 1990s.",
        "language": "en"
    },
    {
        "document_id": "tech_002",
        "text": "Blockchain is a distributed ledger technology where data is stored in a chain of blocks, each cryptographically linked to the previous one. It underpins cryptocurrencies like Bitcoin and enables decentralised, tamper-resistant record-keeping.",
        "language": "en"
    },
    {
        "document_id": "tech_003",
        "text": "Cloud computing delivers computing services—including servers, storage, databases, networking, software, and analytics—over the Internet. Major providers include Amazon Web Services (AWS), Microsoft Azure, and Google Cloud.",
        "language": "en"
    },
    {
        "document_id": "tech_004",
        "text": "Cybersecurity protects computer systems, networks, and data from digital attacks, theft, and damage. Key practices include encryption, firewalls, multi-factor authentication, regular software updates, and security audits.",
        "language": "en"
    },
    {
        "document_id": "tech_005",
        "text": "Python is a high-level, interpreted programming language known for its clear syntax and readability. It is widely used in web development, data science, artificial intelligence, automation, and scientific computing.",
        "language": "en"
    },
    {
        "document_id": "tech_006",
        "text": "The smartphone revolution began with the launch of Apple's iPhone in 2007. Modern smartphones combine phone, camera, computer, GPS, and internet functionality in a pocket-sized device.",
        "language": "en"
    },
    {
        "document_id": "tech_007",
        "text": "Artificial Intelligence (AI) refers to the simulation of human intelligence in machines programmed to think and learn. Applications include self-driving cars, medical diagnosis, language translation, and recommendation systems.",
        "language": "en"
    },
    {
        "document_id": "tech_008",
        "text": "The Web Speech API enables web developers to incorporate voice recognition and text-to-speech synthesis directly in modern browser environments without external audio transmission.",
        "language": "en"
    },
    {
        "document_id": "tech_009",
        "text": "5G is the fifth generation of wireless mobile technology, offering speeds up to 100 times faster than 4G, ultra-low latency, and the ability to connect massive numbers of devices. It enables IoT, autonomous vehicles, and real-time communication.",
        "language": "en"
    },
    {
        "document_id": "tech_010",
        "text": "Open source software is software with source code that anyone can inspect, modify, and distribute. Notable examples include the Linux kernel, the Python language, and the Apache web server.",
        "language": "en"
    },

    # ── Economics & Finance ───────────────────────────────────────────────────
    {
        "document_id": "eco_001",
        "text": "Gross Domestic Product (GDP) is the total monetary value of all goods and services produced within a country's borders in a given time period. It is the primary measure of a country's economic output and health.",
        "language": "en"
    },
    {
        "document_id": "eco_002",
        "text": "Inflation is the rate at which the general level of prices for goods and services rises over time, eroding purchasing power. Central banks manage inflation through monetary policy tools such as interest rate adjustments.",
        "language": "en"
    },
    {
        "document_id": "eco_003",
        "text": "The stock market is a marketplace where buyers and sellers trade shares of publicly listed companies. Major stock exchanges include the New York Stock Exchange (NYSE), NASDAQ, Bombay Stock Exchange (BSE), and London Stock Exchange.",
        "language": "en"
    },
    {
        "document_id": "eco_004",
        "text": "India's economic growth in recent years has been driven by rapid digital public infrastructure (DPI), manufacturing incentives like the Production Linked Incentive (PLI) scheme, and expanding technology services exports.",
        "language": "en"
    },
    {
        "document_id": "eco_005",
        "text": "Supply and demand is a fundamental economic model describing price determination in a free market. When demand exceeds supply, prices rise; when supply exceeds demand, prices fall.",
        "language": "en"
    },
    {
        "document_id": "eco_006",
        "text": "Cryptocurrency is a digital or virtual currency secured by cryptography. Bitcoin, Ethereum, and thousands of altcoins operate on decentralised blockchain networks without central bank control.",
        "language": "en"
    },

    # ── Space & Astronomy ─────────────────────────────────────────────────────
    {
        "document_id": "space_001",
        "text": "The Solar System consists of the Sun and all celestial bodies gravitationally bound to it, including eight planets (Mercury, Venus, Earth, Mars, Jupiter, Saturn, Uranus, Neptune), dwarf planets, moons, asteroids, and comets.",
        "language": "en"
    },
    {
        "document_id": "space_002",
        "text": "The Moon is Earth's only natural satellite. It orbits Earth at an average distance of about 384,400 km. The Apollo 11 mission in 1969 achieved the first crewed lunar landing, with Neil Armstrong as the first human to walk on the Moon.",
        "language": "en"
    },
    {
        "document_id": "space_003",
        "text": "Mars, often called the Red Planet due to its iron oxide surface, is the fourth planet from the Sun. NASA's Perseverance rover and Ingenuity helicopter are currently exploring its surface, searching for signs of ancient microbial life.",
        "language": "en"
    },
    {
        "document_id": "space_004",
        "text": "The James Webb Space Telescope (JWST), launched in December 2021, is the most powerful space telescope ever built. It observes the universe in infrared light and has captured images of galaxies formed shortly after the Big Bang.",
        "language": "en"
    },
    {
        "document_id": "space_005",
        "text": "A light-year is the distance light travels in one year in a vacuum, approximately 9.461 trillion kilometres. It is used as a unit of measurement for vast astronomical distances between stars and galaxies.",
        "language": "en"
    },

    # ── Environment & Ecology ─────────────────────────────────────────────────
    {
        "document_id": "env_001",
        "text": "Biodiversity refers to the variety of life on Earth, encompassing the diversity of species, genes, and ecosystems. High biodiversity increases ecosystem resilience and provides essential services like pollination, clean water, and climate regulation.",
        "language": "en"
    },
    {
        "document_id": "env_002",
        "text": "Renewable energy sources—including solar, wind, hydroelectric, and geothermal power—are naturally replenished and produce little or no greenhouse gas emissions. They are central to global strategies to combat climate change.",
        "language": "en"
    },
    {
        "document_id": "env_003",
        "text": "Plastic pollution is a critical environmental problem. Millions of tonnes of plastic waste enter the oceans annually, harming marine life and entering the food chain as microplastics ingested by fish and humans.",
        "language": "en"
    },
    {
        "document_id": "env_004",
        "text": "Deforestation, the clearing of forests for agriculture, logging, or development, destroys habitat, reduces biodiversity, releases stored carbon, and disrupts water cycles. The Amazon rainforest is a major area of concern.",
        "language": "en"
    },

    # ── Culture, Arts & Literature ────────────────────────────────────────────
    {
        "document_id": "art_001",
        "text": "Shakespeare, born in Stratford-upon-Avon in 1564, is widely regarded as the greatest writer in the English language. His works include 37 plays such as Hamlet, Macbeth, Romeo and Juliet, and 154 sonnets.",
        "language": "en"
    },
    {
        "document_id": "art_002",
        "text": "The Mona Lisa, painted by Leonardo da Vinci between 1503 and 1519, is the world's most famous painting. It hangs in the Louvre Museum in Paris and is celebrated for the subject's enigmatic smile.",
        "language": "en"
    },
    {
        "document_id": "art_003",
        "text": "Bollywood is the informal name for the Hindi-language film industry based in Mumbai (formerly Bombay), India. It is the largest film producer in the world by number of films, producing over 1,500 movies annually.",
        "language": "en"
    },
    {
        "document_id": "art_004",
        "text": "Classical music refers to music produced in, or rooted in, Western traditions of secular and liturgical music. Composers like Bach, Mozart, Beethoven, and Brahms laid the foundations of the Western classical tradition.",
        "language": "en"
    },

    # ── Sports ───────────────────────────────────────────────────────────────
    {
        "document_id": "sport_001",
        "text": "Cricket is one of the most popular sports in the world, especially in South Asia, Australia, England, and the Caribbean. The International Cricket Council (ICC) governs the sport globally. India, Australia, and England are historically dominant teams.",
        "language": "en"
    },
    {
        "document_id": "sport_002",
        "text": "Association football (soccer) is the world's most popular sport, played by over 250 million players in more than 200 countries. The FIFA World Cup, held every four years, is the most-watched sporting event globally.",
        "language": "en"
    },
    {
        "document_id": "sport_003",
        "text": "The Olympic Games are the world's foremost international multi-sport event, held every four years. The Summer Olympics and Winter Olympics alternate every two years. They originated in ancient Greece and were revived in 1896 in Athens.",
        "language": "en"
    },
    {
        "document_id": "sport_004",
        "text": "Tennis is a global sport played individually (singles) or between two teams of two players (doubles). The four Grand Slam tournaments are the Australian Open, French Open, Wimbledon, and US Open.",
        "language": "en"
    },

    # ── Food & Nutrition ──────────────────────────────────────────────────────
    {
        "document_id": "food_001",
        "text": "A balanced diet contains the right proportions of macronutrients—carbohydrates, proteins, and fats—as well as micronutrients like vitamins and minerals. It supports immune function, energy, growth, and disease prevention.",
        "language": "en"
    },
    {
        "document_id": "food_002",
        "text": "Proteins are large biomolecules made up of amino acid chains. They perform a vast array of functions in the body including catalysing metabolic reactions, providing structural support, and transmitting signals.",
        "language": "en"
    },
    {
        "document_id": "food_003",
        "text": "Indian cuisine is known for its bold flavours, diverse spices, and regional variety. Popular dishes include biryani, butter chicken, dal, dosas, idlis, and various curries. Spices like turmeric, cumin, and cardamom are staples.",
        "language": "en"
    },

    # ── Philosophy & Social Sciences ──────────────────────────────────────────
    {
        "document_id": "phil_001",
        "text": "Democracy is a system of government in which citizens exercise power directly or through elected representatives. Key principles include free elections, rule of law, separation of powers, and protection of individual rights.",
        "language": "en"
    },
    {
        "document_id": "phil_002",
        "text": "Philosophy is the study of fundamental questions about existence, knowledge, values, reason, mind, and language. Major branches include metaphysics, epistemology, ethics, aesthetics, and logic.",
        "language": "en"
    },
    {
        "document_id": "phil_003",
        "text": "The United Nations (UN) was founded in 1945 after World War II to maintain international peace and security, develop friendly relations among nations, and promote social progress and human rights. It has 193 member states.",
        "language": "en"
    },

    # ── Language & Communication ──────────────────────────────────────────────
    {
        "document_id": "lang_001",
        "text": "Hindi is an Indo-Aryan language spoken predominantly in India. It is one of the two official languages of the Indian government (the other being English) and is the third most spoken language in the world.",
        "language": "en"
    },
    {
        "document_id": "lang_002",
        "text": "English is a West Germanic language and the most widely used language in the world for international communication, business, and science. It is the official or co-official language in over 60 countries.",
        "language": "en"
    },
    {
        "document_id": "lang_003",
        "text": "Sarvam AI provides high-performance Speech-to-Text (STT) models tailored for Indian languages including Hindi, Tamil, Telugu, Bengali, Kannada, and Indian English. It converts spoken audio into accurate transcripts with low latency.",
        "language": "en"
    },

    # ── Notable People ────────────────────────────────────────────────────────
    {
        "document_id": "people_001",
        "text": "Mahatma Gandhi (1869–1948) was an Indian lawyer and anti-colonial nationalist who led India's independence movement against British rule through nonviolent civil disobedience. He is honoured in India as the 'Father of the Nation'.",
        "language": "en"
    },
    {
        "document_id": "people_002",
        "text": "Albert Einstein (1879–1955) was a German-born theoretical physicist who developed the theory of relativity and made foundational contributions to quantum mechanics. He received the Nobel Prize in Physics in 1921.",
        "language": "en"
    },
    {
        "document_id": "people_003",
        "text": "Marie Curie (1867–1934) was a Polish-French physicist and chemist who conducted pioneering research on radioactivity. She was the first woman to win a Nobel Prize and the only person to win in two different sciences (Physics 1903, Chemistry 1911).",
        "language": "en"
    },
    {
        "document_id": "people_004",
        "text": "Elon Musk is a South African-born entrepreneur and business magnate. He is the founder or co-founder of Tesla, SpaceX, Neuralink, and the Boring Company, and has been a transformative figure in electric vehicles and commercial space exploration.",
        "language": "en"
    },
    {
        "document_id": "people_005",
        "text": "Sundar Pichai is an Indian-American business executive who serves as the CEO of Alphabet Inc. and its subsidiary Google LLC. He grew up in Chennai, India, and studied at IIT Kharagpur before earning degrees at Stanford and Wharton.",
        "language": "en"
    },

    # ── Infrastructure & Engineering ──────────────────────────────────────────
    {
        "document_id": "infra_001",
        "text": "The Great Wall of China is a series of fortifications built along China's historical northern borders to protect against nomadic invasions. Stretching over 21,000 km, it is one of the greatest engineering feats in history.",
        "language": "en"
    },
    {
        "document_id": "infra_002",
        "text": "The Eiffel Tower, constructed between 1887 and 1889 as the entrance arch for the 1889 World's Fair, stands 330 metres tall in Paris, France. It was designed by engineer Gustave Eiffel and receives about 7 million visitors annually.",
        "language": "en"
    },
    {
        "document_id": "infra_003",
        "text": "The Panama Canal is an artificial 82-km waterway in Panama connecting the Atlantic and Pacific Oceans. Completed in 1914, it allows ships to avoid sailing around the southern tip of South America, dramatically reducing travel time.",
        "language": "en"
    },

    # ── Indian Context ────────────────────────────────────────────────────────
    {
        "document_id": "india_001",
        "text": "India's space agency, ISRO (Indian Space Research Organisation), achieved a historic milestone with Chandrayaan-3 in August 2023, successfully landing near the Moon's south pole—a region never previously explored by any nation.",
        "language": "en"
    },
    {
        "document_id": "india_002",
        "text": "The Taj Mahal, located in Agra, Uttar Pradesh, is a white marble mausoleum built by Mughal Emperor Shah Jahan in memory of his wife Mumtaz Mahal. It was completed around 1648 and is a UNESCO World Heritage Site.",
        "language": "en"
    },
    {
        "document_id": "india_003",
        "text": "The Indian Premier League (IPL) is a professional Twenty20 cricket league founded in 2008 by the Board of Control for Cricket in India (BCCI). It is one of the most popular and commercially successful cricket leagues in the world.",
        "language": "en"
    },
    {
        "document_id": "india_004",
        "text": "UPI (Unified Payments Interface) is an instant real-time payment system developed by NPCI (National Payments Corporation of India). It allows users to transfer money between bank accounts instantly via mobile phones and is one of the world's most successful digital payment platforms.",
        "language": "en"
    },
    {
        "document_id": "india_005",
        "text": "India has a rich tradition of classical dance forms including Bharatanatyam, Kathak, Odissi, Kuchipudi, Manipuri, and Mohiniyattam. These dances have roots in ancient Hindu temples and texts like Natyashastra.",
        "language": "en"
    },
]


def load_msmarco_xi_dataset(dataset_name: str = "ai4bharat/MSMARCO-XI", max_docs: int = 1000) -> List[Dict[str, Any]]:
    """
    Attempts to load MSMARCO-XI dataset via HuggingFace datasets library.
    Falls back gracefully to a broad, general-purpose knowledge dataset covering
    science, history, geography, health, technology, culture, and more.
    """
    try:
        from datasets import load_dataset
        print(f"[DatasetLoader] Attempting to load {dataset_name} from Hugging Face...")
        ds = load_dataset(dataset_name, split="train", streaming=True)
        docs = []
        for idx, item in enumerate(ds):
            if idx >= max_docs:
                break
            doc_id = item.get("doc_id", item.get("id", f"msmarco_doc_{idx}"))
            text = item.get("text", item.get("passage", item.get("content", "")))
            if text:
                docs.append({
                    "document_id": str(doc_id),
                    "text": str(text).strip(),
                    "language": item.get("language", "en")
                })
        if docs:
            print(f"[DatasetLoader] Successfully loaded {len(docs)} documents from {dataset_name}.")
            return docs
    except Exception as e:
        print(f"[DatasetLoader] Notice: HuggingFace load exception ({e}). Utilizing enriched offline general-knowledge dataset.")

    # Expand the general-knowledge corpus to fill the requested index size
    expanded_docs = []
    base_count = len(SAMPLE_MSMARCO_XI_DOCUMENTS)
    for i in range(max_docs):
        base = SAMPLE_MSMARCO_XI_DOCUMENTS[i % base_count]
        expanded_docs.append({
            "document_id": f"{base['document_id']}_{i // base_count}" if i >= base_count else base["document_id"],
            "text": base["text"],
            "language": base.get("language", "en")
        })
    print(f"[DatasetLoader] Prepared {len(expanded_docs)} general-knowledge passages for indexing ({base_count} unique topics).")
    return expanded_docs
