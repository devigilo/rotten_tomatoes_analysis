import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import seaborn as sns
import numpy as np
import argparse
from datetime import datetime, timedelta
import re

class RTScoreEvolution:
    def __init__(self, file_path, movie_name=None, release_date=None, days_cutoff=None):
        """
        Initialize with review CSV file path
        
        Args:
            file_path: Path to the CSV file with reviews
            movie_name: Name of the movie
            release_date: Release date of the movie (str in format 'YYYY-MM-DD')
            days_cutoff: Number of days after release to include (None for all reviews)
        """
        self.file_path = file_path
        self.movie_name = movie_name
        self.release_date = release_date
        self.days_cutoff = days_cutoff
        self.data = None
        self.daily_scores = None
        self.cumulative_scores = None
    
    def load_data(self):
        """Load review data from CSV file"""
        try:
            self.data = pd.read_csv(self.file_path)
            print(f"Loaded {len(self.data)} reviews from {self.file_path}")
            
            # If no movie name provided, try to extract from filename
            if not self.movie_name:
                filename = self.file_path.split('/')[-1]
                movie_match = re.match(r'([A-Za-z_]+)_\d{8}_\d{6}\.csv', filename)
                if movie_match:
                    self.movie_name = movie_match.group(1).replace('_', ' ')
                else:
                    self.movie_name = "Movie"
            
            return True
        except Exception as e:
            print(f"Error loading file: {e}")
            return False
    
    def process_dates(self):
        """Process and standardize review dates"""
        if self.data is None:
            return False
        
        if 'Date' not in self.data.columns:
            print("Error: No 'Date' column found in the data")
            return False
        
        # Make a copy of the data to avoid modifying the original
        self.data = self.data.copy()
        
        # Fill missing dates
        self.data['Date'] = self.data['Date'].fillna('Unknown')
        
        # Print some sample dates to help with debugging
        print("\nSample dates from the data:")
        sample_dates = self.data['Date'].sample(min(5, len(self.data))).tolist()
        for date in sample_dates:
            print(f"  {date}")
        
        # For the specific format "Mar 3, 2017"
        def parse_rt_date(date_str):
            """Parse dates in Rotten Tomatoes format: 'Mar 3, 2017'"""
            if date_str == 'Unknown' or pd.isnull(date_str):
                return None
            
            date_str = date_str.strip()
            
            # Try the main RT format: "Mar 3, 2017"
            try:
                return datetime.strptime(date_str, '%b %d, %Y')
            except ValueError:
                pass
            
            # Alternative format with full month name: "March 3, 2017"
            try:
                return datetime.strptime(date_str, '%B %d, %Y')
            except ValueError:
                pass
            
            # Custom regex for more flexibility
            pattern = r'([A-Za-z]{3,})\s+(\d{1,2}),?\s+(\d{4})'
            match = re.match(pattern, date_str)
            
            if match:
                month, day, year = match.groups()
                month_abbr = month[:3].capitalize()  # Take first 3 letters
                
                try:
                    date_str_reformatted = f"{month_abbr} {int(day):d}, {year}"
                    return datetime.strptime(date_str_reformatted, '%b %d, %Y')
                except ValueError:
                    print(f"Could not parse date: {date_str}")
                    return None
            
            print(f"Could not parse date: {date_str}")
            return None
        
        # Apply date parsing
        self.data['Clean Date'] = self.data['Date'].apply(parse_rt_date)
        
        # Calculate how many dates we successfully parsed
        parsed_count = self.data['Clean Date'].notna().sum()
        parsed_pct = (parsed_count / len(self.data)) * 100
        
        print(f"Successfully parsed {parsed_count}/{len(self.data)} dates ({parsed_pct:.1f}%)")
        
        if parsed_count == 0:
            print("\nWARNING: No dates could be parsed. Using artificial dates for visualization.")
            # Create artificial dates for demonstration
            if self.release_date:
                try:
                    release_date = datetime.strptime(self.release_date, '%Y-%m-%d')
                except ValueError:
                    release_date = datetime(2017, 3, 17)  # Default to Beauty and the Beast release date
            else:
                release_date = datetime(2017, 3, 17)  # Default to Beauty and the Beast release date
                
            self.data['Clean Date'] = [release_date + timedelta(days=i) for i in range(len(self.data))]
            parsed_count = len(self.data)
        
        # Filter to only reviews with valid dates for further analysis
        self.data_with_dates = self.data[self.data['Clean Date'].notna()].copy()
        
        # Apply days cutoff if specified
        if self.days_cutoff is not None and self.release_date is not None:
            try:
                release_date = datetime.strptime(self.release_date, '%Y-%m-%d')
                cutoff_date = release_date + timedelta(days=self.days_cutoff)
                
                # Filter to reviews before the cutoff date
                original_count = len(self.data_with_dates)
                self.data_with_dates = self.data_with_dates[self.data_with_dates['Clean Date'] <= cutoff_date]
                filtered_count = len(self.data_with_dates)
                
                print(f"Applied {self.days_cutoff}-day cutoff: kept {filtered_count}/{original_count} reviews")
                
                # If we filtered out all reviews, revert to using all reviews
                if filtered_count == 0:
                    print("Warning: No reviews remain after applying cutoff. Using all reviews.")
                    self.data_with_dates = self.data[self.data['Clean Date'].notna()].copy()
            except ValueError:
                print(f"Warning: Invalid release date format. Using all reviews.")
        
        # Sort by date
        self.data_with_dates = self.data_with_dates.sort_values('Clean Date')
        
        # Print date range
        min_date = self.data_with_dates['Clean Date'].min()
        max_date = self.data_with_dates['Clean Date'].max()
        print(f"Date range: {min_date.strftime('%Y-%m-%d')} to {max_date.strftime('%Y-%m-%d')}")
        
        return parsed_count > 0
    
    def calculate_daily_scores(self):
        """Calculate daily review counts and scores"""
        if self.data_with_dates is None or len(self.data_with_dates) == 0:
            return False
        
        # Add a date-only column for grouping
        self.data_with_dates['Review Date'] = self.data_with_dates['Clean Date'].dt.date
        
        # Determine which column has the sentiment information
        if 'Sentiment' in self.data_with_dates.columns:
            sentiment_col = 'Sentiment'
        elif 'Review Score' in self.data_with_dates.columns:
            sentiment_col = 'Review Score'
        else:
            print("Error: No sentiment/score column found")
            return False
        
        # Add a numeric score column (1 for positive/fresh, 0 for negative/rotten)
        pos_values = ['positive', 'fresh']
        self.data_with_dates['Is Positive'] = self.data_with_dates[sentiment_col].str.lower().isin(pos_values).astype(int)
        
        # Group by date and calculate daily metrics
        daily_stats = self.data_with_dates.groupby('Review Date').agg(
            Daily_Count=('Is Positive', 'count'),
            Daily_Positive=('Is Positive', 'sum')
        )
        
        daily_stats['Daily_Pct_Fresh'] = (daily_stats['Daily_Positive'] / daily_stats['Daily_Count']) * 100
        
        # Add cumulative metrics
        daily_stats['Cumulative_Count'] = daily_stats['Daily_Count'].cumsum()
        daily_stats['Cumulative_Positive'] = daily_stats['Daily_Positive'].cumsum()
        daily_stats['Cumulative_Pct_Fresh'] = (daily_stats['Cumulative_Positive'] / daily_stats['Cumulative_Count']) * 100
        
        # Reset index to make date a column
        self.daily_scores = daily_stats.reset_index()
        
        # Fill in missing dates with no reviews
        date_range = pd.date_range(
            start=self.daily_scores['Review Date'].min(),
            end=self.daily_scores['Review Date'].max()
        )
        
        # Convert to just dates
        date_range = [d.date() for d in date_range]
        
        # Create a complete DataFrame with all dates
        complete_dates = pd.DataFrame({'Review Date': date_range})
        
        # Merge with our actual data
        self.daily_scores = pd.merge(
            complete_dates, 
            self.daily_scores, 
            on='Review Date', 
            how='left'
        )
        
        # Fill NaN values appropriately
        # Days with no reviews should have 0 count, but maintain the previous cumulative values
        self.daily_scores['Daily_Count'] = self.daily_scores['Daily_Count'].fillna(0)
        self.daily_scores['Daily_Positive'] = self.daily_scores['Daily_Positive'].fillna(0)
        self.daily_scores['Daily_Pct_Fresh'] = self.daily_scores['Daily_Pct_Fresh'].fillna(0)
        
        # Forward fill cumulative values
        self.daily_scores['Cumulative_Count'] = self.daily_scores['Cumulative_Count'].fillna(method='ffill').fillna(0)
        self.daily_scores['Cumulative_Positive'] = self.daily_scores['Cumulative_Positive'].fillna(method='ffill').fillna(0)
        self.daily_scores['Cumulative_Pct_Fresh'] = self.daily_scores['Cumulative_Pct_Fresh'].fillna(method='ffill').fillna(0)
        
        return True
    
    def plot_score_evolution(self, output_file=None):
        """Plot the evolution of Rotten Tomatoes score over time"""
        if self.daily_scores is None or len(self.daily_scores) == 0:
            print("No daily score data available to plot")
            return False
        
        # Create a figure with two subplots
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 10), gridspec_kw={'height_ratios': [3, 1]})
        
        # Convert Review Date to datetime for better x-axis handling
        self.daily_scores['Review Date DateTime'] = pd.to_datetime(self.daily_scores['Review Date'])
        
        # Plot 1: Cumulative RT score over time
        ax1.plot(
            self.daily_scores['Review Date DateTime'], 
            self.daily_scores['Cumulative_Pct_Fresh'],
            marker='o',
            linestyle='-',
            linewidth=2,
            markersize=6,
            color='tomato'
        )
        
        # Add 60% line (the "fresh" threshold)
        ax1.axhline(y=60, color='forestgreen', linestyle='--', alpha=0.7, label='Fresh Threshold (60%)')
        
        # Set labels and title
        ax1.set_ylabel('Cumulative % Fresh', fontsize=12)
        title = f'Rotten Tomatoes Score Evolution: {self.movie_name}'
        if self.days_cutoff is not None:
            title += f' (First {self.days_cutoff} Days After Release)'
        ax1.set_title(title, fontsize=16)
        
        # Format the date ticks nicely
        date_format = mdates.DateFormatter('%b %d')
        ax1.xaxis.set_major_formatter(date_format)
        
        # Set the x-axis major locator based on the date range
        date_range = (self.daily_scores['Review Date DateTime'].max() - 
                       self.daily_scores['Review Date DateTime'].min()).days
        
        if date_range <= 7:
            # For a week or less, show each day
            ax1.xaxis.set_major_locator(mdates.DayLocator())
        elif date_range <= 30:
            # For about a month, show every few days
            ax1.xaxis.set_major_locator(mdates.DayLocator(interval=2))
        elif date_range <= 90:
            # For a few months, show weekly ticks
            ax1.xaxis.set_major_locator(mdates.WeekdayLocator(byweekday=0))  # Mondays
        else:
            # For longer periods, show monthly ticks
            ax1.xaxis.set_major_locator(mdates.MonthLocator())
        
        plt.setp(ax1.get_xticklabels(), rotation=45, ha='right')
        
        # Set y-axis to go from 0 to 100
        ax1.set_ylim(0, 100)
        
        # Add data point labels (but not for every point to avoid clutter)
        # Only label points where there were reviews and every 3rd point for dense data
        points_to_label = self.daily_scores[(self.daily_scores['Daily_Count'] > 0)]
        
        # If too many points, sample them
        if len(points_to_label) > 10:
            points_to_label = points_to_label.iloc[::len(points_to_label)//10]
        
        for i, row in points_to_label.iterrows():
            ax1.annotate(
                f"{row['Cumulative_Pct_Fresh']:.1f}%",
                (row['Review Date DateTime'], row['Cumulative_Pct_Fresh']),
                textcoords="offset points",
                xytext=(0, 10),
                ha='center',
                fontsize=9
            )
        
        # Add final score label
        final_row = self.daily_scores.iloc[-1]
        cutoff_label = ""
        if self.days_cutoff is not None:
            cutoff_label = f" ({self.days_cutoff}-day cutoff)"
            
        ax1.annotate(
            f"Final: {final_row['Cumulative_Pct_Fresh']:.1f}% ({int(final_row['Cumulative_Positive'])}/{int(final_row['Cumulative_Count'])}){cutoff_label}",
            (final_row['Review Date DateTime'], final_row['Cumulative_Pct_Fresh']),
            textcoords="offset points", 
            xytext=(20, 0), 
            ha='left',
            fontsize=12,
            weight='bold',
            bbox=dict(boxstyle="round,pad=0.3", fc="white", ec="gray", alpha=0.8)
        )
        
        # Add legend
        ax1.legend()
        
        # Add grid
        ax1.grid(True, alpha=0.3)
        
        # Plot 2: Daily review counts
        bars = ax2.bar(
            self.daily_scores['Review Date DateTime'],
            self.daily_scores['Daily_Count'],
            width=timedelta(days=0.8),
            alpha=0.7,
            color='steelblue'
        )
        
        # Add a line for the daily percentage
        ax3 = ax2.twinx()
        ax3.plot(
            self.daily_scores['Review Date DateTime'],
            self.daily_scores['Daily_Pct_Fresh'],
            marker='x',
            linestyle='--',
            color='darkred',
            alpha=0.7
        )
        
        # Set labels
        ax2.set_xlabel('Review Date', fontsize=12)
        ax2.set_ylabel('Daily Review Count', fontsize=12)
        ax3.set_ylabel('Daily % Fresh', fontsize=12)
        
        # Set y-axis for percentage to go from 0 to 100
        ax3.set_ylim(0, 100)
        
        # Add labels to bars with non-zero counts
        for bar, count in zip(bars, self.daily_scores['Daily_Count']):
            if count > 0:
                height = bar.get_height()
                ax2.text(
                    bar.get_x() + bar.get_width()/2.,
                    height,
                    int(count),
                    ha='center',
                    va='bottom',
                    fontsize=9
                )
        
        # Share x-axis with top plot
        ax2.sharex(ax1)
        ax2.xaxis.set_major_formatter(date_format)
        
        # Customize x-axis for bottom plot
        plt.setp(ax2.get_xticklabels(), rotation=45, ha='right')
        
        # Adjust layout
        plt.tight_layout()
        
        # Add a marker for release date if provided
        if self.release_date:
            try:
                release_date = datetime.strptime(self.release_date, '%Y-%m-%d')
                
                # Add release date marker to both plots
                for ax in [ax1, ax2]:
                    ax.axvline(x=release_date, color='blue', linestyle='-', alpha=0.5, linewidth=1.5)
                    ax.text(release_date, ax.get_ylim()[1]*0.95, 'Release', 
                           rotation=90, va='top', ha='right', color='blue', alpha=0.7)
                
                # Add cutoff date marker if applicable
                if self.days_cutoff is not None:
                    cutoff_date = release_date + timedelta(days=self.days_cutoff)
                    for ax in [ax1, ax2]:
                        ax.axvline(x=cutoff_date, color='red', linestyle='--', alpha=0.5, linewidth=1.5)
                        ax.text(cutoff_date, ax.get_ylim()[1]*0.95, f'{self.days_cutoff}-Day Cutoff', 
                               rotation=90, va='top', ha='right', color='red', alpha=0.7)
            except ValueError:
                print(f"Warning: Could not add release date marker due to invalid date format.")
        
        # Save or show plot
        if output_file:
            plt.savefig(output_file, dpi=300, bbox_inches='tight')
            print(f"Plot saved to {output_file}")
        else:
            plt.show()
        
        plt.close()
        
        return True
    
    def save_daily_data(self, output_file=None):
        """Save the daily score data to a CSV file"""
        if self.daily_scores is None:
            return False
            
        if output_file is None:
            movie_name = self.movie_name.replace(' ', '_')
            cutoff_suffix = f"_{self.days_cutoff}d" if self.days_cutoff is not None else ""
            output_file = f"{movie_name}{cutoff_suffix}_daily_scores.csv"
        
        self.daily_scores.to_csv(output_file, index=False)
        print(f"Daily score data saved to {output_file}")
        return True

def main():
    parser = argparse.ArgumentParser(description='Track Rotten Tomatoes score evolution over time with optional date cutoff')
    parser.add_argument('--file', required=True, help='Path to the CSV file with reviews')
    parser.add_argument('--movie-name', help='Name of the movie (optional, will try to extract from filename)')
    parser.add_argument('--release-date', help='Release date of the movie in YYYY-MM-DD format')
    parser.add_argument('--days-cutoff', type=int, help='Only include reviews within this many days after release')
    parser.add_argument('--output', help='Path to save the plot image')
    parser.add_argument('--save-data', action='store_true', help='Save the daily score data to CSV')
    
    args = parser.parse_args()
    
    tracker = RTScoreEvolution(
        args.file, 
        movie_name=args.movie_name,
        release_date=args.release_date,
        days_cutoff=args.days_cutoff
    )
    
    if not tracker.load_data():
        print("Failed to load review data")
        return
        
    if not tracker.process_dates():
        print("Failed to process review dates")
        return
        
    if not tracker.calculate_daily_scores():
        print("Failed to calculate daily scores")
        return
        
    tracker.plot_score_evolution(args.output)
    
    if args.save_data:
        tracker.save_daily_data()

if __name__ == "__main__":
    main()
