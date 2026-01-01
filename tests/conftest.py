import pytest
import csv

@pytest.fixture
def sample_csv(tmp_path):
    """Generates a rich temporary dataset."""
    d = tmp_path / "data"
    d.mkdir()
    p = d / "test_data.csv"
    
    header = ["id", "date", "customer_name", "category", "rating", "cost", "review", "verified"]
    rows = [
        ["1001", "2023-10-01", "Alice Smith", "Electronics", "5", "299.99", "Absolutely love this device! Works perfectly out of the box.", "True"],
        ["1002", "2023-10-02", "Bob Jones", "Home & Garden", "2", "45.50", "Item arrived broken and the color is wrong. Very disappointed.", "True"],
        ["1003", "2023-10-02", "Charlie Day", "Electronics", "", "120.00", "It's okay but battery life could be better.", "False"],
        ["1004", "2023-10-03", "Diana Prince", "Beauty", "5", "25.00", "Amazing product! Will definitely buy again.", "True"],
        ["1005", "2023-10-04", "Evan Wright", "Home & Garden", "1", "12.99", "Terrible quality. Fell apart in two days. Do not buy.", "True"],
        ["1006", "2023-10-04", "", "Electronics", "4", "89.99", "Good value for money. Shipping was fast.", "False"],
        ["1007", "2023-10-05", "Grace Hopper", "Books", "5", "15.50", "A masterpiece. I couldn't put it down.", "True"],
        ["1008", "2023-10-06", "Hank Pym", "Electronics", "3", "299.99", "Standard performance. Nothing special but gets the job done.", "True"],
        ["1009", "2023-10-07", "Ivy Doom", "Beauty", "", "55.00", "", "False"],
        ["1010", "2023-10-08", "Jack Ryan", "Books", "2", "10.00", "Boring plot and flat characters. Waste of time.", "True"],
        ["1011", "2023-10-09", "Kelly Kapowski", "Home & Garden", "5", "150.00", "Stunning design! Matches my living room perfectly.", "True"],
        ["1012", "2023-10-10", "Leo Fitz", "Electronics", "4", "120.00", "Great features for the price point.", "False"],
        ["1013", "2023-10-11", "Mindy Kaling", "Beauty", "1", "5.00", "Caused an allergic reaction. Beware!", "True"],
        ["1014", "2023-10-12", "Nate Drake", "Books", "5", "22.50", "Best book I've read this year. Highly recommended.", "True"],
        ["1015", "2023-10-12", "Oscar Isaac", "", "3", "45.00", "Average experience. fast delivery though.", "False"],
        ["1016", "2023-10-13", "Peter Parker", "Electronics", "5", "499.00", "Incredible tech! The camera resolution is mind-blowing.", "True"],
        ["1017", "2023-10-14", "Quinn Fabray", "Home & Garden", "2", "30.00", "Smaller than expected.", "True"],
        ["1018", "2023-10-15", "Rachel Green", "Beauty", "5", "32.00", "Love the texture and smell. So luxurious.", "True"],
        ["1019", "2023-10-16", "Steve Rogers", "Books", "4", "18.00", "Solid read with good pacing.", "True"],
        ["1020", "2023-10-17", "Tony Stark", "Electronics", "1", "1200.00", "Overpriced garbage. The interface is buggy.", "True"],
    ]
    
    with open(p, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(header)
        writer.writerows(rows)
        
    return str(p)