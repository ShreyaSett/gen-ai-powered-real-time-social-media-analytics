import json
import random
from datetime import datetime, timedelta
import pytz
import boto3
import time
import traceback
import os

# Initialize AWS client
kinesis_client = boto3.client('kinesis')

# Configuration
STREAM_NAME = 'synthetic_data_stream'

# Global locations list
LOCATIONS = [
    # North America
    "New York USA", "San Francisco USA", "Toronto Canada", "Vancouver Canada", "Mexico City Mexico",
    # Europe
    "London UK", "Paris France", "Berlin Germany", "Amsterdam Netherlands", "Madrid Spain",
    # Asia
    "Tokyo Japan", "Singapore", "Seoul South Korea", "Mumbai India", "Dubai UAE",
    # Oceania
    "Sydney Australia", "Melbourne Australia", "Auckland New Zealand",
    # South America
    "São Paulo Brazil", "Buenos Aires Argentina",
    # Africa
    "Lagos Nigeria", "Cape Town South Africa", "Nairobi Kenya"
]

# Primary trending hashtags with demographic weights
TRENDING_HASHTAGS = {
    "#AIForGood": {
        "posts": [
            "AI detecting early-stage diseases in underserved communities! This is revolutionary",
            "Our AI model just helped prevent a major environmental disaster",
            "Using AI to optimize food distribution to combat hunger",
            "AI-powered education making learning accessible to remote areas"
        ],
        "weight": 25,
        "demographics": {
            "gender": {"male": 0.55, "female": 0.45},
            "age_groups": {"18-25": 0.2, "26-35": 0.4, "36-50": 0.3, "51-65": 0.1}
        }
    },
    "#NeuroDivergentVoices": {
        "posts": [
            "My ADHD helped me see patterns others missed at work today",
            "Companies need to understand neurodiversity is a strength",
            "Why 'normal' workplaces need to change for neurodivergent success",
            "Creating inclusive spaces for all types of minds"
        ],
        "weight": 22,
        "demographics": {
            "gender": {"male": 0.45, "female": 0.55},
            "age_groups": {"18-25": 0.3, "26-35": 0.4, "36-50": 0.2, "51-65": 0.1}
        }
    },
    "#SpaceTourism": {
        "posts": [
            "Just booked my first orbital flight for 2026! Dream come true",
            "Space hotel construction begins - future of tourism is here",
            "Zero-gravity experience was worth every penny",
            "Commercial space flights getting more affordable each year"
        ],
        "weight": 20,
        "demographics": {
            "gender": {"male": 0.60, "female": 0.40},
            "age_groups": {"18-25": 0.15, "26-35": 0.45, "36-50": 0.30, "51-65": 0.10}
        }
    },
    "#KPopFever": {
        "posts": [
            "BTS new album breaking all streaming records!",
            "BLACKPINK world tour tickets sold out in minutes",
            "K-pop choreography taking over social media",
            "Korean music industry revolutionizing entertainment globally"
        ],
        "weight": 24,
        "demographics": {
            "gender": {"male": 0.35, "female": 0.65},
            "age_groups": {"18-25": 0.45, "26-35": 0.35, "36-50": 0.15, "51-65": 0.05}
        }
    },
    "#SwiftieNation": {
        "posts": [
            "Taylor's new era is everything we needed",
            "Eras Tour breaking box office records worldwide",
            "That surprise song last night had me crying",
            "Taylor's songwriting continues to evolve beautifully"
        ],
        "weight": 23,
        "demographics": {
            "gender": {"male": 0.30, "female": 0.70},
            "age_groups": {"18-25": 0.40, "26-35": 0.35, "36-50": 0.20, "51-65": 0.05}
        }
    },
    "#AugmentedReality": {
        "posts": [
            "These AR glasses changed how I navigate cities",
            "AR workplace training reducing errors by 60%",
            "Gaming will never be the same with AR",
            "AR shopping experiences becoming mainstream"
        ],
        "weight": 19,
        "demographics": {
            "gender": {"male": 0.58, "female": 0.42},
            "age_groups": {"18-25": 0.35, "26-35": 0.40, "36-50": 0.20, "51-65": 0.05}
        }
    },
    "#DigitalArt": {
        "posts": [
            "AI-assisted digital art opening new creative possibilities",
            "My NFT collection just dropped!",
            "Digital sculpting is revolutionizing character design",
            "Virtual galleries making art more accessible"
        ],
        "weight": 21,
        "demographics": {
            "gender": {"male": 0.48, "female": 0.52},
            "age_groups": {"18-25": 0.40, "26-35": 0.35, "36-50": 0.20, "51-65": 0.05}
        }
    },
    "#OceanCleanup": {
        "posts": [
            "New technology removes 99% of ocean plastic",
            "Community beach cleanup collected 2 tons today",
            "Innovative solutions for marine conservation",
            "Corporate responsibility in ocean preservation"
        ],
        "weight": 18,
        "demographics": {
            "gender": {"male": 0.45, "female": 0.55},
            "age_groups": {"18-25": 0.35, "26-35": 0.30, "36-50": 0.25, "51-65": 0.10}
        }
    },
    "#RemoteWork": {
        "posts": [
            "Digital nomad life is the future",
            "Virtual team building actually works!",
            "Best productivity tools for remote teams",
            "Work-life balance finally achieved thanks to remote work"
        ],
        "weight": 20,
        "demographics": {
            "gender": {"male": 0.52, "female": 0.48},
            "age_groups": {"18-25": 0.25, "26-35": 0.45, "36-50": 0.25, "51-65": 0.05}
        }
    },
    "#FastFashion": {
        "posts": [
            "The true cost of fast fashion on our planet",
            "Sustainable alternatives to fast fashion trends",
            "Thrifting is the new shopping",
            "Why fast fashion brands need to change"
        ],
        "weight": 17,
        "demographics": {
            "gender": {"male": 0.35, "female": 0.65},
            "age_groups": {"18-25": 0.40, "26-35": 0.35, "36-50": 0.20, "51-65": 0.05}
        }
    }
}

# Secondary topics with demographic targeting
SECONDARY_TOPICS = {
    "Fashion": {
        "brands": {
            "Gucci": {
                "posts": {
                    "positive": [
                        "New Gucci collection is absolutely stunning! Worth every penny",
                        "The sustainability focus in Gucci's latest line is impressive",
                        "Gucci's attention to detail is unmatched in luxury fashion"
                    ],
                    "negative": [
                        "Gucci prices getting a bit too steep lately",
                        "Quality issues with my recent Gucci purchase"
                    ],
                    "neutral": [
                        "Comparing Gucci's new collection with other luxury brands",
                        "Interesting design choices in Gucci's latest release"
                    ]
                },
                "weight": 8,
                "demographics": {
                    "gender": {"female": 0.7, "male": 0.3},
                    "age_groups": {"18-25": 0.3, "26-35": 0.4, "36-50": 0.2, "51-65": 0.1}
                }
            },
            "Zara": {
                "posts": {
                    "positive": [
                        "Zara's new collection perfectly balances style and affordability",
                        "Their sustainable line is actually amazing quality",
                        "Fast fashion done right - great designs at good prices"
                    ],
                    "negative": [
                        "Sizing inconsistency is frustrating",
                        "Website crashes during sales are annoying"
                    ],
                    "neutral": [
                        "New collection giving major designer vibes",
                        "Interesting to see their seasonal transition pieces"
                    ]
                },
                "weight": 7,
                "demographics": {
                    "gender": {"female": 0.75, "male": 0.25},
                    "age_groups": {"18-25": 0.4, "26-35": 0.35, "36-50": 0.15, "51-65": 0.1}
                }
            },
            "Nike": {
                "posts": {
                    "positive": [
                        "These Air Max are game changers for my workouts",
                        "Nike's innovation in athletic wear is unmatched",
                        "Their sustainable line performs incredibly well"
                    ],
                    "negative": [
                        "Price points getting too high",
                        "Limited stock on popular sizes"
                    ],
                    "neutral": [
                        "Comparing the new release with previous models",
                        "Interesting colorway choices this season"
                    ]
                },
                "weight": 9,
                "demographics": {
                    "gender": {"female": 0.45, "male": 0.55},
                    "age_groups": {"18-25": 0.35, "26-35": 0.4, "36-50": 0.15, "51-65": 0.1}
                }
            },
            "H&M": {
                "posts": {
                    "positive": [
                        "H&M's conscious collection is so affordable yet stylish",
                        "Their basics are perfect for everyday wear",
                        "Love their designer collaborations"
                    ],
                    "negative": [
                        "Online sizes never match store sizes",
                        "Wish they'd improve fabric quality"
                    ],
                    "neutral": [
                        "New collection just dropped - mixed feelings",
                        "Comparing their sustainable line with competitors"
                    ]
                },
                "weight": 7,
                "demographics": {
                    "gender": {"female": 0.70, "male": 0.30},
                    "age_groups": {"18-25": 0.45, "26-35": 0.35, "36-50": 0.15, "51-65": 0.05}
                }
            },
            "Uniqlo": {
                "posts": {
                    "positive": [
                        "Uniqlo's HEATTECH is perfect for winter",
                        "Their minimalist designs go with everything",
                        "Best quality basics for the price"
                    ],
                    "negative": [
                        "Limited style variety compared to competitors",
                        "Wish they had more locations"
                    ],
                    "neutral": [
                        "New technical fabric collection review",
                        "Comparing their basics with other brands"
                    ]
                },
                "weight": 6,
                "demographics": {
                    "gender": {"female": 0.55, "male": 0.45},
                    "age_groups": {"18-25": 0.35, "26-35": 0.40, "36-50": 0.20, "51-65": 0.05}
                }
            },
            "Levi's": {
                "posts": {
                    "positive": [
                        "These 501s get better with every wear",
                        "Their vintage fits are unbeatable",
                        "New sustainable denim line is impressive"
                    ],
                    "negative": [
                        "Price increases are getting steep",
                        "Inconsistent sizing between styles"
                    ],
                    "neutral": [
                        "Breaking in raw denim journey",
                        "Comparing different fits and washes"
                    ]
                },
                "weight": 7,
                "demographics": {
                    "gender": {"female": 0.45, "male": 0.55},
                    "age_groups": {"18-25": 0.30, "26-35": 0.35, "36-50": 0.25, "51-65": 0.10}
                }
            },
            "Lululemon": {
                "posts": {
                    "positive": [
                        "These leggings are worth every penny",
                        "Perfect for both workout and casual wear",
                        "Their quality never disappoints"
                    ],
                    "negative": [
                        "Getting too expensive for athleisure",
                        "Limited size range needs improvement"
                    ],
                    "neutral": [
                        "New fabric technology review",
                        "Comparing with other athletic brands"
                    ]
                },
                "weight": 8,
                "demographics": {
                    "gender": {"female": 0.80, "male": 0.20},
                    "age_groups": {"18-25": 0.35, "26-35": 0.40, "36-50": 0.20, "51-65": 0.05}
                }
            },
            "Chanel": {
                "posts": {
                    "positive": [
                        "Classic flap bag is still the best investment",
                        "Their new collection is breathtaking",
                        "Boutique experience is unmatched"
                    ],
                    "negative": [
                        "Price increases are getting ridiculous",
                        "Waitlists are getting longer"
                    ],
                    "neutral": [
                        "Analyzing latest runway collection",
                        "Comparing vintage vs new pieces"
                    ]
                },
                "weight": 9,
                "demographics": {
                    "gender": {"female": 0.85, "male": 0.15},
                    "age_groups": {"18-25": 0.20, "26-35": 0.35, "36-50": 0.35, "51-65": 0.10}
                }
            },
            "Dior": {
                "posts": {
                    "positive": [
                        "New Book Tote designs are stunning",
                        "Their makeup line is exceptional",
                        "Couture show was revolutionary"
                    ],
                    "negative": [
                        "Quality doesn't always match the price",
                        "Customer service inconsistency"
                    ],
                    "neutral": [
                        "Analyzing seasonal collections",
                        "Comparing with other luxury houses"
                    ]
                },
                "weight": 8,
                "demographics": {
                    "gender": {"female": 0.80, "male": 0.20},
                    "age_groups": {"18-25": 0.25, "26-35": 0.35, "36-50": 0.30, "51-65": 0.10}
                }
            },
            "Adidas": {
                "posts": {
                    "positive": [
                        "Boost technology still unmatched",
                        "Their sustainable line is impressive",
                        "Perfect for both sports and style"
                    ],
                    "negative": [
                        "Website crashes during hype releases",
                        "Limited stock on popular models"
                    ],
                    "neutral": [
                        "Comparing different boost models",
                        "Analyzing their collaboration strategy"
                    ]
                },
                "weight": 8,
                "demographics": {
                    "gender": {"female": 0.40, "male": 0.60},
                    "age_groups": {"18-25": 0.40, "26-35": 0.35, "36-50": 0.20, "51-65": 0.05}
                }
            },
            "Puma": {
                "posts": {
                    "positive": [
                        "Their motorsport line is fire",
                        "Best value for performance wear",
                        "Collaborations are getting better"
                    ],
                    "negative": [
                        "Limited availability in some regions",
                        "Durability issues with some models"
                    ],
                    "neutral": [
                        "Reviewing new running line",
                        "Comparing with other sports brands"
                    ]
                },
                "weight": 7,
                "demographics": {
                    "gender": {"female": 0.35, "male": 0.65},
                    "age_groups": {"18-25": 0.40, "26-35": 0.35, "36-50": 0.20, "51-65": 0.05}
                }
            }
        }
    },
    "Sports": {
        "leagues": {
            "NBA": {
                "posts": {
                    "positive": [
                        "This season's playoff race is incredible!",
                        "That game-winning shot was legendary",
                        "Rookie class showing amazing potential"
                    ],
                    "negative": [
                        "Refs making too many controversial calls",
                        "Load management is ruining regular season"
                    ],
                    "neutral": [
                        "Analyzing the new playoff format",
                        "Interesting trades before the deadline"
                    ]
                },
                "weight": 9,
                "demographics": {
                    "gender": {"female": 0.35, "male": 0.65},
                    "age_groups": {"18-25": 0.35, "26-35": 0.35, "36-50": 0.20, "51-65": 0.10}
                }
            },
            "F1": {
                "posts": {
                    "positive": [
                        "This season's technical regulations making racing exciting",
                        "Amazing overtake at the last corner!",
                        "New team showing promising pace"
                    ],
                    "negative": [
                        "Race strategy ruined potential podium",
                        "Cost cap controversies need addressing"
                    ],
                    "neutral": [
                        "Analyzing new aerodynamic packages",
                        "Interesting tire choices for the weekend"
                    ]
                },
                "weight": 8,
                "demographics": {
                    "gender": {"female": 0.30, "male": 0.70},
                    "age_groups": {"18-25": 0.30, "26-35": 0.40, "36-50": 0.20, "51-65": 0.10}
                }
            },
            "NFL": {
                "posts": {
                    "positive": [
                        "This year's QB class is exceptional",
                        "Sunday Night Football never disappoints",
                        "Playoff race is getting intense"
                    ],
                    "negative": [
                        "Too many roughing the passer calls",
                        "Thursday games affecting performance"
                    ],
                    "neutral": [
                        "Analyzing new offensive schemes",
                        "Draft prospects evaluation"
                    ]
                },
                "weight": 9,
                "demographics": {
                    "gender": {"female": 0.30, "male": 0.70},
                    "age_groups": {"18-25": 0.30, "26-35": 0.35, "36-50": 0.25, "51-65": 0.10}
                }
            },
            "FIFA/UEFA": {
                "posts": {
                    "positive": [
                        "Champions League nights are magical",
                        "World Cup qualifiers getting intense",
                        "New generation of talent emerging"
                    ],
                    "negative": [
                        "VAR decisions still controversial",
                        "Too many matches in calendar"
                    ],
                    "neutral": [
                        "Analyzing new competition formats",
                        "Transfer market developments"
                    ]
                },
                "weight": 9,
                "demographics": {
                    "gender": {"female": 0.25, "male": 0.75},
                    "age_groups": {"18-25": 0.35, "26-35": 0.35, "36-50": 0.20, "51-65": 0.10}
                }
            },
            "Cricket": {
                "posts": {
                    "positive": [
                        "Test cricket at its finest today",
                        "IPL auction breaks records again",
                        "ICC tournament format improving"
                    ],
                    "negative": [
                        "Rain rules need updating",
                        "Too many T20 leagues"
                    ],
                    "neutral": [
                        "Analyzing pitch conditions",
                        "Comparing different formats"
                    ]
                },
                "weight": 7,
                "demographics": {
                    "gender": {"female": 0.20, "male": 0.80},
                    "age_groups": {"18-25": 0.30, "26-35": 0.35, "36-50": 0.25, "51-65": 0.10}
                }
            },
            "Tennis": {
                "posts": {
                    "positive": [
                        "Grand Slam final was epic",
                        "Next gen players showing promise",
                        "Court conditions perfect today"
                    ],
                    "negative": [
                        "Schedule too demanding",
                        "Prize money distribution issues"
                    ],
                    "neutral": [
                        "Analyzing new serving techniques",
                        "Comparing different surfaces"
                    ]
                },
                "weight": 7,
                "demographics": {
                    "gender": {"female": 0.45, "male": 0.55},
                    "age_groups": {"18-25": 0.25, "26-35": 0.35, "36-50": 0.30, "51-65": 0.10}
                }
            },
            "E-sports": {
                "posts": {
                    "positive": [
                        "Worlds championship viewership record",
                        "Amazing clutch in CSGO major",
                        "New meta making games exciting"
                    ],
                    "negative": [
                        "Server issues during tournament",
                        "Balance patches too frequent"
                    ],
                    "neutral": [
                        "Analyzing team compositions",
                        "Pro player transfer news"
                    ]
                },
                "weight": 8,
                "demographics": {
                    "gender": {"female": 0.25, "male": 0.75},
                    "age_groups": {"18-25": 0.45, "26-35": 0.35, "36-50": 0.15, "51-65": 0.05}
                }
            },
            "College_Sports": {
                "posts": {
                    "positive": [
                        "March Madness bracket busters",
                        "Bowl season getting exciting",
                        "Conference championships thriller"
                    ],
                    "negative": [
                        "NIL deals creating imbalance",
                        "Transfer portal chaos"
                    ],
                    "neutral": [
                        "Analyzing recruiting classes",
                        "Conference realignment impact"
                    ]
                },
                "weight": 7,
                "demographics": {
                    "gender": {"female": 0.35, "male": 0.65},
                    "age_groups": {"18-25": 0.40, "26-35": 0.30, "36-50": 0.20, "51-65": 0.10}
                }
            }
        }
    },
    "AnyCompany": {
        "standalone": {
            "positive": [
                "AnyCompany's new UI is so intuitive",
                "Love how AnyCompany protects user privacy",
                "The content discovery algorithm is spot on",
                "Community guidelines making this a safer space",
                "New creator tools are game-changing",
                "Finally, a platform that understands work-life balance",
                "Their support team responds within minutes!"
            ],
            "negative": [
                "App crashed during peak hours",
                "Need more customization options",
                "Notification system needs work",
                "Missing some basic features"
            ],
            "neutral": [
                "New feature rollout happening gradually",
                "Platform demographics shifting",
                "Interesting content moderation approach",
                "Creator economy evolving on the platform"
            ]
        },
        "comparisons": {
            "Instagram": {
                "better": [
                    "AnyCompany's photo quality beats Instagram hands down",
                    "Much better privacy settings than Instagram",
                    "Creator monetization way more transparent than Instagram",
                    "No more algorithmic feed issues like on Instagram"
                ],
                "worse": [
                    "Instagram's story features still more advanced than AnyCompany",
                    "Missing Instagram's robust filter system",
                    "Instagram's shop integration is more seamless"
                ],
                "neutral": [
                    "Different approach to reels than Instagram",
                    "Engagement patterns vary from Instagram"
                ]
            },
            "Twitter": {
                "better": [
                    "AnyCompany's verification system makes more sense than Twitter",
                    "No character limits like Twitter",
                    "More civilized discussions than Twitter",
                    "Better content moderation than Twitter"
                ],
                "worse": [
                    "Twitter's real-time news spread is still faster",
                    "Missing Twitter's thread functionality",
                    "Twitter's hashtag system more established"
                ],
                "neutral": [
                    "Different approach to trending topics than Twitter",
                    "Community dynamics vary from Twitter"
                ]
            },
            "TikTok": {
                "better": [
                    "AnyCompany's video editor more professional than TikTok",
                    "Better data privacy than TikTok",
                    "More diverse content than just short videos",
                    "Creator fund more sustainable than TikTok"
                ],
                "worse": [
                    "TikTok's sound library is more extensive",
                    "TikTok's challenges get more engagement",
                    "Missing TikTok's duet feature"
                ],
                "neutral": [
                    "Different content recommendation system than TikTok",
                    "Audience retention patterns vary from TikTok"
                ]
            },
            "Facebook": {
                "better": [
                    "AnyCompany's group features more organized than Facebook",
                    "Cleaner feed than Facebook's ad-heavy experience",
                    "Better privacy controls than Facebook",
                    "More youth engagement than Facebook"
                ],
                "worse": [
                    "Facebook's event planning features still superior",
                    "Facebook's marketplace more established",
                    "Missing Facebook's robust business tools"
                ],
                "neutral": [
                    "Different approach to communities than Facebook",
                    "User demographics vary from Facebook"
                ]
            },
            "Threads": {
                "better": [
                    "AnyCompany's engagement features better than Threads",
                    "More stable platform than Threads",
                    "Better content discovery than Threads",
                    "More active user base than Threads"
                ],
                "worse": [
                    "Threads' Instagram integration is smoother",
                    "Threads' simple UI has advantages",
                    "Missing Threads' cross-posting features"
                ],
                "neutral": [
                    "Different posting style than Threads",
                    "User behavior patterns vary from Threads"
                ]
            }
        },
        "demographics": {
            "gender": {"female": 0.52, "male": 0.48},
            "age_groups": {"18-25": 0.35, "26-35": 0.40, "36-50": 0.20, "51-65": 0.05}
        },
        "weight": 10
    }
}

# Helper Functions
def select_demographics(demographic_weights):
    """Select gender and age based on demographic weights"""
    try:
        gender = random.choices(
            list(demographic_weights["gender"].keys()),
            weights=list(demographic_weights["gender"].values())
        )[0]
        
        age_group = random.choices(
            list(demographic_weights["age_groups"].keys()),
            weights=list(demographic_weights["age_groups"].values())
        )[0]
        
        age_ranges = {
            "18-25": (18, 25),
            "26-35": (26, 35),
            "36-50": (36, 50),
            "51-65": (51, 65)
        }
        min_age, max_age = age_ranges[age_group]
        specific_age = random.randint(min_age, max_age)
        
        return gender, specific_age, age_group
    except Exception as e:
        print(f"Error in select_demographics: {str(e)}")
        return "female", 25, "18-25"
def calculate_engagement_metrics(base_weight, demographics):
    """Calculate engagement metrics based on various factors"""
    try:
        base_multiplier = base_weight / 10
        
        # Age group multiplier
        age_group = demographics[2]
        age_multiplier = 1.2 if age_group in ["18-25", "26-35"] else 1.0
        
        # Random variation
        variation = random.uniform(0.8, 1.2)
        
        # Calculate final metrics
        base_engagement = random.randint(100, 1000)
        total_multiplier = base_multiplier * age_multiplier * variation
        
        engagement = {
            "likes": int(base_engagement * total_multiplier * random.uniform(1.0, 2.0)),
            "retweets": int(base_engagement * total_multiplier * random.uniform(0.3, 0.7)),
            "replies": int(base_engagement * total_multiplier * random.uniform(0.1, 0.4))
        }
        
        return engagement
    except Exception as e:
        print(f"Error in calculate_engagement_metrics: {str(e)}")
        return {"likes": 100, "retweets": 20, "replies": 10}

def generate_post_id():
    """Generate a unique post ID"""
    timestamp = int(time.time() * 1000)
    random_suffix = random.randint(1000, 9999)
    return f"p{timestamp}{random_suffix}"

def get_current_timestamp():
    """Get current timestamp in UTC"""
    return datetime.now(pytz.UTC).strftime("%Y-%m-%d %H:%M:%S UTC")

def validate_post_content(content, max_length=280):
    """Validate and clean post content"""
    if not content:
        return False, "Empty content"
    
    content = ' '.join(content.split())
    
    if len(content) > max_length:
        content = content[:max_length-3] + "..."
    
    return True, content

def generate_deceptive_post():
    """Generate a deceptively crafted post with suspicious patterns"""
    try:
        suspicious_patterns = [
            {
                "content": f"Make ${random.randint(1000,10000)} daily! DM for secret method!",
                "hashtags": ["#EasyMoney", "#GetRichQuick"]
            },
            {
                "content": f"FREE {random.choice(['iPhone15', 'MacBook', 'PS5'])}! Click: {random.choice(['bit.ly/win', 'tinyurl.com/prize'])}",
                "hashtags": ["#Giveaway", "#FreePrize"]
            },
            {
                "content": f"URGENT: Account security check required! Verify here: {random.choice(['securelogin.net', 'verify-account.com'])}",
                "hashtags": ["#Security", "#Urgent"]
            },
            {
                "content": f"Investment opportunity! {random.randint(500,1000)}% guaranteed returns in 24hrs!",
                "hashtags": ["#Investment", "#Crypto"]
            },
            {
                "content": f"EXCLUSIVE DEAL! Limited spots! Join now: {random.choice(['exclusive-offer.net', 'special-deal.com'])}",
                "hashtags": ["#Exclusive", "#Limited"]
            }
        ]
        
        chosen_pattern = random.choice(suspicious_patterns)
        
        # Generate artificially high engagement
        engagement = {
            "likes": random.randint(50000, 100000),
            "retweets": random.randint(25000, 50000),
            "replies": random.randint(10000, 25000)
        }

        return {
            "post_id": generate_post_id(),
            "timestamp": get_current_timestamp(),
            "username": f"user_{random.randint(100000, 999999)}_{random.randint(1000, 9999)}",
            "location": random.choice(LOCATIONS),
            "language": "en",
            "content": chosen_pattern["content"],
            "hashtags": chosen_pattern["hashtags"][:1],  # Keep one hashtag to match other posts
            "mentions": [f"@user_{random.randint(1000, 9999)}" for _ in range(5)],
            "topic": "promotion",
            "engagement": engagement,
            "source": random.choice(["web", "mobile", "unknown"]),
            "user_age": random.randint(18, 25),
            "user_gender": random.choice(["male", "female"]),
            "post_type": "promotional",
            "category": "other",
            "age_group": "18-25"
        }
    except Exception as e:
        print(f"Error in generate_deceptive_post: {str(e)}")
        return None

def generate_trending_post():
    """Generate a trending topic post"""
    try:
        current_time = datetime.now(pytz.UTC) - timedelta(minutes=random.randint(0, 5))
        
        hashtag = random.choices(
            list(TRENDING_HASHTAGS.keys()),
            weights=[data['weight'] for data in TRENDING_HASHTAGS.values()]
        )[0]
        
        topic_data = TRENDING_HASHTAGS[hashtag]
        gender, age, age_group = select_demographics(topic_data["demographics"])
        content = random.choice(topic_data["posts"])
        
        engagement = calculate_engagement_metrics(
            topic_data['weight'],
            (gender, age, age_group)
        )

        return {
            "post_id": generate_post_id(),
            "timestamp": current_time.strftime("%Y-%m-%d %H:%M:%S UTC"),
            "username": f"user_{random.randint(1000, 9999)}",
            "location": random.choice(LOCATIONS),
            "language": "en",
            "content": f"{content} {hashtag}",
            "hashtags": [hashtag],
            "mentions": [f"@user_{random.randint(1000, 9999)}" for _ in range(random.randint(0, 2))],
            "topic": hashtag.strip('#'),
            "engagement": engagement,
            "source": random.choice(["Android", "iOS", "Web"]),
            "user_age": age,
            "user_gender": gender,
            "post_type": "trending",
            "category": "trending",
            "age_group": age_group
        }
    except Exception as e:
        print(f"Error in generate_trending_post: {str(e)}")
        return None
def generate_secondary_post():
    """Generate a post about secondary topics (fashion, sports)"""
    try:
        category = random.choice(list(SECONDARY_TOPICS.keys()))
        brand = random.choice(list(SECONDARY_TOPICS[category]["brands"].keys()))
        brand_data = SECONDARY_TOPICS[category]["brands"][brand]
        
        gender, age, age_group = select_demographics(brand_data["demographics"])
        sentiment_type = random.choices(["positive", "negative", "neutral"], weights=[0.6, 0.2, 0.2])[0]
        content = random.choice(brand_data["posts"][sentiment_type])
        hashtag = f"#{brand}"
        
        engagement = calculate_engagement_metrics(
            brand_data['weight'],
            (gender, age, age_group)
        )

        return {
            "post_id": generate_post_id(),
            "timestamp": get_current_timestamp(),
            "username": f"user_{random.randint(1000, 9999)}",
            "location": random.choice(LOCATIONS),
            "language": "en",
            "content": f"{content} {hashtag}",
            "hashtags": [hashtag],
            "mentions": [f"@user_{random.randint(1000, 9999)}" for _ in range(random.randint(0, 2))],
            "topic": brand,
            "engagement": engagement,
            "source": random.choice(["Android", "iOS", "Web"]),
            "user_age": age,
            "user_gender": gender,
            "post_type": "secondary",
            "category": category,
            "brand": brand,
            "age_group": age_group
        }
    except Exception as e:
        print(f"Error in generate_secondary_post: {str(e)}")
        return None

def generate_competitor_post():
    """Generate a post comparing competitor features with AnyCompany"""
    try:
        competitor = random.choice(list(COMPETITORS.keys()))
        competitor_data = COMPETITORS[competitor]
        
        gender, age, age_group = select_demographics(competitor_data["demographics"])
        comparison_type = random.choice(["better", "worse"])
        content = random.choice(competitor_data["features"][comparison_type])
        hashtag = f"#{competitor}"
        
        engagement = calculate_engagement_metrics(
            competitor_data['weight'],
            (gender, age, age_group)
        )

        return {
            "post_id": generate_post_id(),
            "timestamp": get_current_timestamp(),
            "username": f"user_{random.randint(1000, 9999)}",
            "location": random.choice(LOCATIONS),
            "language": "en",
            "content": f"{content} {hashtag}",
            "hashtags": [hashtag],
            "mentions": [f"@user_{random.randint(1000, 9999)}" for _ in range(random.randint(0, 2))],
            "topic": f"{competitor} vs AnyCompany",
            "engagement": engagement,
            "source": random.choice(["Android", "iOS", "Web"]),
            "user_age": age,
            "user_gender": gender,
            "post_type": "competitor",
            "platform": competitor,
            "comparison_type": comparison_type,
            "age_group": age_group
        }
    except Exception as e:
        print(f"Error in generate_competitor_post: {str(e)}")
        return None

def generate_mixed_posts(batch_size=15):
    """Generate a mixed batch of posts"""
    posts = []
    distribution = {
        "trending": int(batch_size * 0.6),
        "secondary": int(batch_size * 0.25),
        "competitor": int(batch_size * 0.15)
    }
    
    # Adjust for rounding
    total = sum(distribution.values())
    if total < batch_size:
        distribution["trending"] += batch_size - total
    
    for post_type, count in distribution.items():
        for _ in range(count):
            post = None
            if post_type == "trending":
                post = generate_trending_post()
            elif post_type == "secondary":
                post = generate_secondary_post()
            else:
                post = generate_competitor_post()
            
            if post:
                posts.append(post)
    
    random.shuffle(posts)
    return posts

def validate_post(post):
    """Validate post structure and content"""
    try:
        required_fields = [
            "post_id", "timestamp", "username", "content", 
            "hashtags", "engagement", "user_age",
            "user_gender", "post_type"
        ]
        for field in required_fields:
            if field not in post:
                return False, f"Missing required field: {field}"
        
        if not isinstance(post["hashtags"], list) or len(post["hashtags"]) != 1:
            return False, "Invalid hashtags format or count"
        
        if not all(key in post["engagement"] for key in ["likes", "retweets", "replies"]):
            return False, "Missing engagement metrics"
        
        if not isinstance(post["user_age"], int) or not (18 <= post["user_age"] <= 65):
            return False, "Invalid user age"
        
        if post["user_gender"] not in ["male", "female"]:
            return False, "Invalid user gender"
        
        is_valid_content, cleaned_content = validate_post_content(post["content"])
        if not is_valid_content:
            return False, "Invalid content"
        
        post["content"] = cleaned_content
        
        return True, "Valid post"
    except Exception as e:
        return False, f"Validation error: {str(e)}"

def analyze_distribution(posts):
    """Analyze the distribution of posts"""
    analysis = {
        "total_posts": len(posts),
        "post_types": {},
        "hashtags": {},
        "demographics": {
            "gender": {"male": 0, "female": 0},
            "age_groups": {"18-25": 0, "26-35": 0, "36-50": 0, "51-65": 0}
        },
        "engagement": {
            "total_likes": 0,
            "total_retweets": 0,
            "total_replies": 0,
            "average_engagement_per_post": 0
        },
        "topics": {},
        "temporal_distribution": {}
    }
    
    for post in posts:
        post_type = post["post_type"]
        analysis["post_types"][post_type] = analysis["post_types"].get(post_type, 0) + 1
        
        hashtag = post["hashtags"][0]
        analysis["hashtags"][hashtag] = analysis["hashtags"].get(hashtag, 0) + 1
        
        analysis["demographics"]["gender"][post["user_gender"]] += 1
        analysis["demographics"]["age_groups"][post["age_group"]] += 1
        
        engagement = post["engagement"]
        analysis["engagement"]["total_likes"] += engagement["likes"]
        analysis["engagement"]["total_retweets"] += engagement["retweets"]
        analysis["engagement"]["total_replies"] += engagement["replies"]
        
        topic = post["topic"]
        if topic not in analysis["topics"]:
            analysis["topics"][topic] = {
                "count": 0,
                "engagement": 0
            }
        analysis["topics"][topic]["count"] += 1
        analysis["topics"][topic]["engagement"] += sum(engagement.values())
        
        hour = datetime.strptime(post["timestamp"], "%Y-%m-%d %H:%M:%S UTC").strftime("%H:00")
        analysis["temporal_distribution"][hour] = analysis["temporal_distribution"].get(hour, 0) + 1
    
    if len(posts) > 0:
        total_engagement = (
            analysis["engagement"]["total_likes"] +
            analysis["engagement"]["total_retweets"] +
            analysis["engagement"]["total_replies"]
        )
        analysis["engagement"]["average_engagement_per_post"] = total_engagement / len(posts)
    
    analysis["top_hashtags"] = dict(
        sorted(
            analysis["hashtags"].items(),
            key=lambda x: x[1],
            reverse=True
        )[:10]
    )
    
    return analysis
def lambda_handler(event, context):
    """Main Lambda handler function"""
    try:
        # Get or initialize batch counter from environment variable
        batch_counter = int(os.environ.get('BATCH_COUNTER', 0))
        batch_counter += 1
        
        # Fixed batch size of 15
        batch_size = 15
        records_sent = 0
        failed_records = 0
        errors = []
        
        # Generate regular posts
        posts = generate_mixed_posts(batch_size)
        
        # Every 18th batch, replace one random post with a deceptive post
        if batch_counter % 18 == 0:
            deceptive_post = generate_deceptive_post()
            if deceptive_post:
                replace_index = random.randint(0, len(posts) - 1)
                posts[replace_index] = deceptive_post
                print(f"Inserted deceptive post in batch {batch_counter}")
        
        # Process and send each post
        for post in posts:
            try:
                if not post:
                    failed_records += 1
                    continue
                
                # Validate post
                is_valid, validation_message = validate_post(post)
                if not is_valid:
                    failed_records += 1
                    errors.append(f"Post {post.get('post_id', 'unknown')}: {validation_message}")
                    continue
                
                # Send to Kinesis
                response = kinesis_client.put_record(
                    StreamName=STREAM_NAME,
                    Data=json.dumps(post) + '\n',
                    PartitionKey=str(random.randint(1, 100))
                )
                
                records_sent += 1
                time.sleep(0.1)  # Small delay between records
                
            except Exception as e:
                failed_records += 1
                errors.append(f"Error processing post: {str(e)}")
        
        # Update batch counter in environment
        os.environ['BATCH_COUNTER'] = str(batch_counter)
        
        # Analyze distribution
        distribution_analysis = analyze_distribution(posts)
        
        # Calculate additional metrics
        avg_engagement = 0
        if records_sent > 0:
            total_engagement = sum(
                sum(p["engagement"].values()) for p in posts if p
            )
            avg_engagement = total_engagement / records_sent
        
        # Prepare detailed response
        response = {
            'statusCode': 200 if failed_records == 0 else 207,
            'body': json.dumps({
                'message': f'Processed {len(posts)} posts',
                'batch_details': {
                    'batch_number': batch_counter,
                    'batch_size': batch_size,
                    'successful_records': records_sent,
                    'failed_records': failed_records,
                    'contains_deceptive': (batch_counter % 18 == 0)
                },
                'stream_info': {
                    'stream_name': STREAM_NAME,
                    'average_engagement': avg_engagement
                },
                'distribution': distribution_analysis,
                'timing': {
                    'processed_at': datetime.now(pytz.UTC).isoformat(),
                    'next_batch_due': (
                        datetime.now(pytz.UTC) + timedelta(minutes=5)
                    ).isoformat()
                },
                'errors': errors if errors else None
            }, indent=2)
        }
        
        return response
        
    except Exception as e:
        error_traceback = traceback.format_exc()
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': str(e),
                'message': 'Error in Lambda execution',
                'traceback': error_traceback,
                'error_type': type(e).__name__,
                'timestamp': datetime.now(pytz.UTC).isoformat()
            }, indent=2)
        }

def local_test():
    """Function for local testing"""
    test_event = {
        'batch_size': 15,
        'batch_counter': 0
    }
    
    # Test multiple batches
    for i in range(20):  # Test 20 batches
        test_event['batch_counter'] = i
        print(f"\nProcessing batch {i+1}")
        result = lambda_handler(test_event, None)
        
        # Parse and print relevant information
        response_body = json.loads(result['body'])
        print(f"Status Code: {result['statusCode']}")
        print(f"Successful Records: {response_body.get('batch_details', {}).get('successful_records', 0)}")
        print(f"Contains Deceptive Post: {response_body.get('batch_details', {}).get('contains_deceptive', False)}")
        
        if response_body.get('errors'):
            print("Errors:", response_body['errors'])
        
        time.sleep(1)  # Pause between batches

if __name__ == "__main__":
    local_test()
