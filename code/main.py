import os
import time
import pandas as pd
from agent import SupportAgent, INTER_TICKET_DELAY
from tqdm import tqdm

def main():
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    data_dir = os.path.join(base_dir, 'data')
    input_csv = os.path.join(base_dir, 'support_tickets', 'support_tickets.csv')
    output_csv = os.path.join(base_dir, 'support_tickets', 'output.csv')

    print("Initializing Support Agent and loading corpus...")
    agent = SupportAgent(data_dir=data_dir)

    print(f"Reading input from {input_csv}...")
    try:
        df = pd.read_csv(input_csv)
    except FileNotFoundError:
        print(f"Error: Could not find input file at {input_csv}")
        return

    # --- Resume from checkpoint ---
    # If output.csv exists, load already-processed rows and skip them
    already_done = 0
    existing_results = []
    if os.path.exists(output_csv):
        try:
            existing_df = pd.read_csv(output_csv)
            already_done = len(existing_df)
            existing_results = existing_df.to_dict('records')
            print(f"Resuming: {already_done} tickets already processed, skipping them...")
        except Exception:
            pass  # If corrupt, start fresh

    results = list(existing_results)
    total = len(df)
    remaining = total - already_done
    print(f"Processing {remaining} remaining tickets (with {INTER_TICKET_DELAY}s inter-ticket delay)...")

    for index, row in tqdm(df.iloc[already_done:].iterrows(), total=remaining):
        issue = row.get('Issue', '')
        subject = row.get('Subject', '')
        company = row.get('Company', '')

        output = agent.process_ticket(issue, subject, company)

        results.append({
            'Issue': issue,
            'Subject': subject,
            'Company': company,
            'Response': output.get('response', ''),
            'Product Area': output.get('product_area', ''),
            'Status': output.get('status', ''),
            'Request Type': output.get('request_type', ''),
            'Justification': output.get('justification', '')
        })

        # Save after every ticket (checkpoint) so progress is never lost
        out_df = pd.DataFrame(results)
        out_df.to_csv(output_csv, index=False)

        # Polite pause between tickets to stay inside per-minute token quota
        if index < total - 1:
            time.sleep(INTER_TICKET_DELAY)

    print(f"\nProcessing complete. Output saved to {output_csv}")

if __name__ == "__main__":
    main()
