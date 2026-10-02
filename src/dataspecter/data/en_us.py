"""Bundled data for the locale en_US. Sources and review status are in SOURCES.md."""

COUNTRY = "United States"
POSTCODE_LENGTH = 5

# +1-NXX-555-01XX. Numbers 555-0100 to 555-0199 are reserved for fictional use, so these cannot
# belong to a real subscriber. N is 2 to 9, as area codes do not begin with 0 or 1.
PHONE = (
    ("literal", "+1-"),
    ("two_to_nine", ""),
    ("digit", ""),
    ("digit", ""),
    ("literal", "-555-01"),
    ("digit", ""),
    ("digit", ""),
)

GIVEN_NAMES = (
    "James", "Mary", "Robert", "Patricia", "John", "Jennifer", "Michael", "Linda", "David",
    "Elizabeth", "William", "Barbara", "Richard", "Susan", "Joseph", "Jessica", "Thomas",
    "Sarah", "Charles", "Karen", "Christopher", "Lisa", "Daniel", "Nancy", "Matthew", "Betty",
    "Anthony", "Margaret", "Mark", "Sandra", "Donald", "Ashley", "Steven", "Kimberly", "Paul",
    "Emily", "Andrew", "Donna", "Joshua", "Michelle", "Kenneth", "Carol", "Kevin", "Amanda",
    "Brian", "Dorothy", "George", "Melissa", "Timothy", "Deborah", "Ronald", "Stephanie",
    "Edward", "Rebecca", "Jason", "Sharon", "Jeffrey", "Laura", "Ryan", "Cynthia", "Jacob",
    "Kathleen", "Gary", "Amy", "Nicholas", "Angela", "Eric", "Shirley", "Jonathan", "Anna",
    "Stephen", "Brenda", "Larry", "Pamela", "Justin", "Emma", "Scott", "Nicole", "Brandon",
    "Helen", "Benjamin", "Samantha", "Samuel", "Katherine", "Gregory", "Christine",
    "Alexander", "Debra", "Frank", "Rachel", "Patrick", "Carolyn", "Raymond", "Janet", "Jack",
    "Catherine", "Dennis", "Maria", "Jerry", "Heather", "Tyler", "Diane", "Aaron", "Olivia",
    "Jose", "Julie", "Adam", "Joyce", "Nathan", "Victoria",
)  # fmt: skip

FAMILY_NAMES = (
    "Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller", "Davis", "Rodriguez",
    "Martinez", "Hernandez", "Lopez", "Gonzalez", "Wilson", "Anderson", "Thomas", "Taylor",
    "Moore", "Jackson", "Martin", "Lee", "Perez", "Thompson", "White", "Harris", "Sanchez",
    "Clark", "Ramirez", "Lewis", "Robinson", "Walker", "Young", "Allen", "King", "Wright",
    "Scott", "Torres", "Nguyen", "Hill", "Flores", "Green", "Adams", "Nelson", "Baker", "Hall",
    "Rivera", "Campbell", "Mitchell", "Carter", "Roberts", "Gomez", "Phillips", "Evans",
    "Turner", "Diaz", "Parker", "Cruz", "Edwards", "Collins", "Reyes", "Stewart", "Morris",
    "Morales", "Murphy", "Cook", "Rogers", "Gutierrez", "Ortiz", "Morgan", "Cooper",
    "Peterson", "Bailey", "Reed", "Kelly", "Howard", "Ramos", "Kim", "Cox", "Ward",
    "Richardson", "Watson", "Brooks", "Chavez", "Wood", "James", "Bennett", "Gray", "Mendoza",
    "Ruiz", "Hughes", "Price", "Alvarez", "Castillo", "Sanders", "Patel", "Myers", "Long",
    "Ross", "Foster", "Jimenez", "O'Brien", "O'Connor", "McDonald", "Sullivan",
)  # fmt: skip

STREET_NAMES = (
    "Main Street", "Oak Street", "Maple Avenue", "Cedar Lane", "Pine Street", "Elm Street",
    "Washington Avenue", "Lake Drive", "Hill Road", "Park Avenue", "Sunset Boulevard",
    "River Road", "Church Street", "Highland Avenue", "Lincoln Street", "Jefferson Avenue",
    "Madison Street", "Franklin Street", "Chestnut Street", "Walnut Street", "Spring Street",
    "Willow Lane", "Meadow Lane", "Forest Drive", "Broadway", "Center Street", "Mill Road",
    "Ridge Road", "Cherry Street", "Birch Lane",
)  # fmt: skip

STATES = (
    "Alaska", "Arizona", "California", "Colorado", "Connecticut", "District of Columbia",
    "Florida", "Georgia", "Hawaii", "Idaho", "Illinois", "Indiana", "Iowa", "Kentucky",
    "Louisiana", "Maryland", "Massachusetts", "Michigan", "Minnesota", "Missouri", "Nebraska",
    "Nevada", "New Jersey", "New Mexico", "New York", "North Carolina", "Ohio", "Oklahoma",
    "Oregon", "Pennsylvania", "Rhode Island", "Tennessee", "Texas", "Utah", "Virginia",
    "Washington", "Wisconsin",
)  # fmt: skip

# (city, state, leading digits of the ZIP codes used in that city)
CITIES = (
    ("New York", "New York", ("100",)),
    ("Buffalo", "New York", ("142",)),
    ("Los Angeles", "California", ("900",)),
    ("San Diego", "California", ("921",)),
    ("San Jose", "California", ("951",)),
    ("San Francisco", "California", ("941",)),
    ("Fresno", "California", ("937",)),
    ("Sacramento", "California", ("958",)),
    ("Chicago", "Illinois", ("606",)),
    ("Houston", "Texas", ("770",)),
    ("San Antonio", "Texas", ("782",)),
    ("Dallas", "Texas", ("752",)),
    ("Austin", "Texas", ("787",)),
    ("Fort Worth", "Texas", ("761",)),
    ("El Paso", "Texas", ("799",)),
    ("Phoenix", "Arizona", ("850",)),
    ("Tucson", "Arizona", ("857",)),
    ("Philadelphia", "Pennsylvania", ("191",)),
    ("Pittsburgh", "Pennsylvania", ("152",)),
    ("Jacksonville", "Florida", ("322",)),
    ("Miami", "Florida", ("331",)),
    ("Tampa", "Florida", ("336",)),
    ("Orlando", "Florida", ("328",)),
    ("Columbus", "Ohio", ("432",)),
    ("Cleveland", "Ohio", ("441",)),
    ("Cincinnati", "Ohio", ("452",)),
    ("Charlotte", "North Carolina", ("282",)),
    ("Raleigh", "North Carolina", ("276",)),
    ("Indianapolis", "Indiana", ("462",)),
    ("Seattle", "Washington", ("981",)),
    ("Denver", "Colorado", ("802",)),
    ("Colorado Springs", "Colorado", ("809",)),
    ("Washington", "District of Columbia", ("200",)),
    ("Boston", "Massachusetts", ("021",)),
    ("Nashville", "Tennessee", ("372",)),
    ("Memphis", "Tennessee", ("381",)),
    ("Detroit", "Michigan", ("482",)),
    ("Oklahoma City", "Oklahoma", ("731",)),
    ("Tulsa", "Oklahoma", ("741",)),
    ("Portland", "Oregon", ("972",)),
    ("Las Vegas", "Nevada", ("891",)),
    ("Louisville", "Kentucky", ("402",)),
    ("Baltimore", "Maryland", ("212",)),
    ("Milwaukee", "Wisconsin", ("532",)),
    ("Albuquerque", "New Mexico", ("871",)),
    ("Kansas City", "Missouri", ("641",)),
    ("St. Louis", "Missouri", ("631",)),
    ("Atlanta", "Georgia", ("303",)),
    ("Omaha", "Nebraska", ("681",)),
    ("Minneapolis", "Minnesota", ("554",)),
    ("New Orleans", "Louisiana", ("701",)),
    ("Honolulu", "Hawaii", ("968",)),
    ("Salt Lake City", "Utah", ("841",)),
    ("Anchorage", "Alaska", ("995",)),
    ("Richmond", "Virginia", ("232",)),
    ("Boise", "Idaho", ("837",)),
    ("Des Moines", "Iowa", ("503",)),
    ("Hartford", "Connecticut", ("061",)),
    ("Providence", "Rhode Island", ("029",)),
    ("Newark", "New Jersey", ("071",)),
)
