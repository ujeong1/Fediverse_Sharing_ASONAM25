import time
import re
import string
import csv
from itertools import product
from mastodon import Mastodon
import pandas as pd
from tqdm import tqdm

# ----------------------------- Configuration -----------------------------
ACCESS_TOKEN = "YOUR_ACCESS_TOKEN_HERE"
INSTANCE_URL = "https://mastodon.social"
QUERY_LENGTH = 2
RESULT_LIMIT = 80
MAX_STATUSES = 100
SLEEP_TIME = 1

# ----------------------------- Setup API -----------------------------
mastodon = Mastodon(
    access_token=ACCESS_TOKEN,
    api_base_url=INSTANCE_URL
)

# ----------------------------- Helper Functions -----------------------------
def is_threads_user(acct):
    return acct.endswith("@threads.net")

def generate_queries(length=2):
    return [''.join(p) for p in product(string.ascii_lowercase, repeat=length)]

# ----------------------------- Stage 1: Seed User Collection -----------------------------
def collect_seed_users(queries):
    seen_ids = set()
    results = []

    print("🔎 Stage 1: Seed User Collection")
    for query in tqdm(queries, desc="Searching prefixes"):
        try:
            accounts = mastodon.account_search(query, limit=RESULT_LIMIT)
            for account in accounts:
                if (
                    is_threads_user(account.acct)
                    and account.id not in seen_ids
                    and getattr(account, "discoverable", True)
                    and getattr(account, "indexable", True)
                ):
                    seen_ids.add(account.id)
                    results.append({
                        "user_id": account.id,
                        "acct": account.acct,
                        "username": account.username,
                        "url": account.url
                    })
                    print(f"[+] Found seed: {account.acct}")
            time.sleep(SLEEP_TIME)
        except Exception as e:
            print(f"❌ Error during query '{query}': {e}")
    df = pd.DataFrame(results)
    df.to_csv("stage1_seed_users.csv", index=False)
    print(f"✅ Saved {len(df)} seed users to stage1_seed_users.csv")
    return df

# ----------------------------- Stage 2: User Interaction Collection -----------------------------
def get_user_posts(user_id, limit=MAX_STATUSES):
    try:
        return mastodon.account_statuses(user_id, limit=limit)
    except Exception as e:
        print(f"❌ Error fetching statuses for {user_id}: {e}")
        return []

def collect_repliers_from_post(post):
    try:
        context = mastodon.status_context(post['id'])
        return [
            reply['account'] for reply in context['descendants']
            if is_threads_user(reply['account']['acct'])
        ]
    except Exception as e:
        print(f"❌ Error getting replies for status {post['id']}: {e}")
        return []

# ----------------------------- Stage 3: Snowball Sampling -----------------------------
def snowball_user_collection(initial_users):
    all_known_ids = set(initial_users["user_id"])
    all_users_df = initial_users.copy()
    iteration = 1

    while True:
        new_users = []
        print(f"\n🔄 Stage 3 Iteration {iteration}: Collecting repliers")

        for user_id in tqdm(all_known_ids, desc=f"Iter {iteration} - Collecting posts"):
            posts = get_user_posts(user_id)
            for post in posts:
                repliers = collect_repliers_from_post(post)
                for acc in repliers:
                    if (
                        acc['id'] not in all_known_ids
                        and acc.get('discoverable', True)
                        and acc.get('indexable', True)
                    ):
                        all_known_ids.add(acc['id'])
                        new_users.append({
                            "user_id": acc['id'],
                            "acct": acc['acct'],
                            "username": acc['username'],
                            "url": acc['url']
                        })
                        print(f"[+] New replier: {acc['acct']} ({acc['id']})")

        if not new_users:
            print("✅ No new users found. Stopping iteration.")
            break

        # Save iteration result
        iter_df = pd.DataFrame(new_users)
        iter_filename = f"stage2_interaction_iteration_{iteration}.csv"
        iter_df.to_csv(iter_filename, index=False)
        print(f"📁 Saved {len(iter_df)} new users to {iter_filename}")

        # Merge into full set
        all_users_df = pd.concat([all_users_df, iter_df]).drop_duplicates(subset="user_id")
        iteration += 1
        time.sleep(SLEEP_TIME)

    # Final save
    all_users_df.to_csv("final_threads_users.csv", index=False)
    print(f"\n🎉 Final user set saved to final_threads_users.csv with {len(all_users_df)} unique users.")

# ----------------------------- Pipeline Runner -----------------------------
if __name__ == "__main__":
    prefixes = generate_queries(QUERY_LENGTH)
    seed_df = collect_seed_users(prefixes)
    snowball_user_collection(seed_df)

