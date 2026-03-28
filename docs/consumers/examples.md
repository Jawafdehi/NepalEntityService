# Examples

Practical examples for common use cases with the Nepal Entity Service API.

## Basic Examples

### Search for a Person

Search for a person by name:

```python
import requests

response = requests.get(
    "https://nes.jawafdehi.org/api/entities",
    params={
        "query": "ram chandra poudel",
        "entity_type": "person"
    }
)

data = response.json()
print(f"Found {data['total']} results")

for entity in data['entities']:
    name = entity['names'][0]['en']['full']
    party = entity['attributes'].get('party', 'Unknown')
    print(f"- {name} ({party})")
```

### Get Entity Details

Retrieve complete information about an entity:

```python
import requests

entity_id = "entity:person/ram-chandra-poudel"
response = requests.get(f"https://nes.jawafdehi.org/api/entities/{entity_id}")

entity = response.json()

# Print basic info
print(f"Name: {entity['names'][0]['en']['full']}")
print(f"Type: {entity['type']}")

# Print attributes
print("\nAttributes:")
for key, value in entity['attributes'].items():
    print(f"  {key}: {value}")

# Print identifiers
print("\nExternal Links:")
for identifier in entity['identifiers']:
    if identifier.get('url'):
        print(f"  {identifier['scheme']}: {identifier['url']}")
```

### Find All Members of a Political Party

Query relationships to find all members of a party:

```python
import requests

party_id = "entity:organization/political_party/nepali-congress"
response = requests.get(
    "https://nes.jawafdehi.org/api/relationships",
    params={
        "relationship_type": "MEMBER_OF",
        "target_entity_id": party_id,
        "limit": 50
    }
)

data = response.json()
print(f"Found {data['total']} members")

# Get details for each member
for rel in data['relationships']:
    person_id = rel['source_entity_id']
    person_response = requests.get(f"https://nes.jawafdehi.org/api/entities/{person_id}")
    person = person_response.json()
    
    name = person['names'][0]['en']['full']
    role = rel['attributes'].get('role', 'Member')
    print(f"- {name} ({role})")
```

## Advanced Examples

### Filter by Tags - 2079 Federal Election Results

Tags allow you to categorize entities into groups. Here's a complete example of analyzing the 2079 Federal election results:

```python
import requests
from collections import Counter

# Fetch all 2079 Federal election elected representatives
response = requests.get(
    "https://nes.jawafdehi.org/api/entities",
    params={
        "entity_type": "person",
        "tags": "federal-election-2079-elected",
        "limit": 500  # Adjust based on total elected representatives
    }
)

data = response.json()
print(f"Total 2079 Federal Election Elected Representatives: {data['total']}\n")

# Display first 10 elected representatives with their details
print("Sample Elected Representatives:")
print("=" * 70)
for entity in data['entities'][:10]:
    name = entity['names'][0]['en']['full']
    nepali_name = entity['names'][0].get('ne', {}).get('full', 'N/A')
    party = entity['attributes'].get('party', 'Independent')
    constituency = entity['attributes'].get('constituency', 'Unknown')

    print(f"Name: {name}")
    if nepali_name != 'N/A':
        print(f"  Nepali: {nepali_name}")
    print(f"  Party: {party}")
    print(f"  Constituency: {constituency}")
    print()

# Analyze results by party
print("\nElection Results by Party:")
print("=" * 70)

party_counts = Counter()
for entity in data['entities']:
    party = entity['attributes'].get('party', 'Independent')
    party_counts[party] += 1

for party, count in party_counts.most_common():
    percentage = (count / data['total']) * 100
    print(f"{party:35} {count:3} seats ({percentage:.1f}%)")

print("=" * 70)
print(f"Total Seats: {data['total']}")
```

**Filter candidates vs elected representatives:**

```python
import requests

# Get all candidates (including those who didn't win)
candidates_response = requests.get(
    "https://nes.jawafdehi.org/api/entities",
    params={
        "entity_type": "person",
        "tags": "federal-election-2079-candidate"
    }
)

# Get only elected representatives
elected_response = requests.get(
    "https://nes.jawafdehi.org/api/entities",
    params={
        "entity_type": "person",
        "tags": "federal-election-2079-elected"
    }
)

candidates = candidates_response.json()
elected = elected_response.json()

print(f"Total Candidates: {candidates['total']}")
print(f"Total Elected: {elected['total']}")
print(f"Success Rate: {(elected['total'] / candidates['total'] * 100):.1f}%")
```

**Combine tags with text search:**

```python
import requests

# Find all elected representatives with "poudel" in their name
response = requests.get(
    "https://nes.jawafdehi.org/api/entities",
    params={
        "query": "poudel",
        "entity_type": "person",
        "tags": "federal-election-2079-elected"
    }
)

data = response.json()
print(f"Found {data['total']} elected representatives named Poudel:\n")

for entity in data['entities']:
    name = entity['names'][0]['en']['full']
    constituency = entity['attributes'].get('constituency', 'Unknown')
    party = entity['attributes'].get('party', 'Independent')
    print(f"- {name} ({constituency}, {party})")
```

**Compare federal and provincial elections:**

```python
import requests

# Get federal election winners
federal_response = requests.get(
    "https://nes.jawafdehi.org/api/entities",
    params={
        "entity_type": "person",
        "tags": "federal-election-2079-elected"
    }
)

# Get provincial election winners
provincial_response = requests.get(
    "https://nes.jawafdehi.org/api/entities",
    params={
        "entity_type": "person",
        "tags": "provincial-election-2079-elected"
    }
)

federal = federal_response.json()
provincial = provincial_response.json()

print("2079 Election Results Summary:")
print(f"  Federal Election: {federal['total']} seats")
print(f"  Provincial Election: {provincial['total']} seats")
print(f"  Total Elected: {federal['total'] + provincial['total']} representatives")
```

**Track candidates across elections (2079 to 2082):**

```python
import requests

# Get 2082 Federal election candidates
response_2082 = requests.get(
    "https://nes.jawafdehi.org/api/entities",
    params={
        "entity_type": "person",
        "tags": "federal-election-2082-candidate"
    }
)

candidates_2082 = response_2082.json()['entities']

print(f"Analyzing {len(candidates_2082)} candidates for 2082 election:\n")

# For each 2082 candidate, check if they were in 2079 election
for candidate in candidates_2082[:10]:  # Show first 10
    name = candidate['names'][0]['en']['full']
    tags = candidate.get('tags', [])

    print(f"{name}:")

    # Check if they were candidates or elected in 2079
    if 'federal-election-2079-elected' in tags:
        print("  ✓ Elected in 2079 Federal election (incumbent)")
    elif 'federal-election-2079-candidate' in tags:
        print("  • Candidate in 2079 Federal election (re-running)")
    else:
        print("  ⭐ First-time federal candidate")

    print()
```

### Search with Multiple Filters

Combine multiple filters for precise results:

```python
import requests
import json

response = requests.get(
    "https://nes.jawafdehi.org/api/entities",
    params={
        "query": "pradesh",
        "entity_type": "location",
        "sub_type": "province",
        "attributes": json.dumps({"population": ">5000000"}),
        "limit": 10
    }
)

data = response.json()
for location in data['entities']:
    name = location['names'][0]['en']['full']
    pop = location['attributes'].get('population', 'Unknown')
    print(f"{name}: {pop} people")
```

### Paginate Through Large Result Sets

Handle pagination for large datasets:

```python
import requests

def get_all_entities(entity_type, page_size=20):
    """Fetch all entities of a given type with pagination."""
    all_entities = []
    offset = 0
    
    while True:
        response = requests.get(
            "https://nes.jawafdehi.org/api/entities",
            params={
                "entity_type": entity_type,
                "limit": page_size,
                "offset": offset
            }
        )
        
        data = response.json()
        all_entities.extend(data['entities'])
        
        # Check if we've fetched all results
        if offset + page_size >= data['total']:
            break
        
        offset += page_size
    
    return all_entities

# Get all political parties
parties = get_all_entities("organization")
print(f"Total parties: {len(parties)}")
```

### Track Entity Changes Over Time

View version history to see how an entity changed:

```python
import requests
from datetime import datetime

entity_id = "entity:person/ram-chandra-poudel"

# Get version history
response = requests.get(f"https://nes.jawafdehi.org/api/entities/{entity_id}/versions")
versions = response.json()['versions']

print(f"Entity has {len(versions)} versions\n")

for version in versions:
    created_at = datetime.fromisoformat(version['created_at'].replace('Z', '+00:00'))
    author = version['author']
    description = version.get('change_description', 'No description')
    
    print(f"Version {version['version_number']}:")
    print(f"  Date: {created_at.strftime('%Y-%m-%d %H:%M')}")
    print(f"  By: {author}")
    print(f"  Change: {description}")
    
    # Show what changed
    snapshot = version['snapshot']
    party = snapshot['attributes'].get('party', 'Unknown')
    position = snapshot['attributes'].get('position', 'Unknown')
    print(f"  State: {party}, {position}\n")
```

### Build a Relationship Graph

Create a network graph of entity relationships:

```python
import requests
import networkx as nx
import matplotlib.pyplot as plt

def build_relationship_graph(entity_id, depth=2):
    """Build a relationship graph starting from an entity."""
    G = nx.DiGraph()
    visited = set()
    
    def add_relationships(entity_id, current_depth):
        if current_depth > depth or entity_id in visited:
            return
        
        visited.add(entity_id)
        
        # Get entity details
        entity_response = requests.get(f"https://nes.jawafdehi.org/api/entities/{entity_id}")
        entity = entity_response.json()
        entity_name = entity['names'][0]['en']['full']
        
        # Add node
        G.add_node(entity_id, label=entity_name, type=entity['type'])
        
        # Get relationships
        rel_response = requests.get(
            f"https://nes.jawafdehi.org/api/entities/{entity_id}/relationships"
        )
        relationships = rel_response.json()['relationships']
        
        for rel in relationships:
            target_id = rel['target_entity_id']
            rel_type = rel['type']
            
            # Add edge
            G.add_edge(entity_id, target_id, type=rel_type)
            
            # Recursively add target's relationships
            add_relationships(target_id, current_depth + 1)
    
    add_relationships(entity_id, 0)
    return G

# Build graph
entity_id = "entity:person/ram-chandra-poudel"
G = build_relationship_graph(entity_id, depth=2)

print(f"Graph has {G.number_of_nodes()} nodes and {G.number_of_edges()} edges")

# Visualize (requires matplotlib)
pos = nx.spring_layout(G)
labels = nx.get_node_attributes(G, 'label')
nx.draw(G, pos, labels=labels, with_labels=True, node_color='lightblue', 
        node_size=1500, font_size=8, arrows=True)
plt.show()
```

## Web Application Examples

### React Component

Fetch and display entities in a React component:

```javascript
import React, { useState, useEffect } from 'react';

function EntitySearch() {
  const [query, setQuery] = useState('');
  const [entities, setEntities] = useState([]);
  const [loading, setLoading] = useState(false);

  const searchEntities = async () => {
    setLoading(true);
    try {
      const response = await fetch(
        `https://nes.jawafdehi.org/api/entities?query=${encodeURIComponent(query)}`
      );
      const data = await response.json();
      setEntities(data.entities);
    } catch (error) {
      console.error('Error fetching entities:', error);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div>
      <input
        type="text"
        value={query}
        onChange={(e) => setQuery(e.target.value)}
        placeholder="Search entities..."
      />
      <button onClick={searchEntities} disabled={loading}>
        {loading ? 'Searching...' : 'Search'}
      </button>

      <div>
        {entities.map((entity) => (
          <div key={entity.id}>
            <h3>{entity.names[0].en.full}</h3>
            <p>Type: {entity.type}</p>
            {entity.attributes.party && (
              <p>Party: {entity.attributes.party}</p>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}

export default EntitySearch;
```

### Vue.js Component

Similar functionality in Vue.js:

```vue
<template>
  <div>
    <input
      v-model="query"
      @keyup.enter="searchEntities"
      placeholder="Search entities..."
    />
    <button @click="searchEntities" :disabled="loading">
      {{ loading ? 'Searching...' : 'Search' }}
    </button>

    <div v-for="entity in entities" :key="entity.id">
      <h3>{{ entity.names[0].en.full }}</h3>
      <p>Type: {{ entity.type }}</p>
      <p v-if="entity.attributes.party">
        Party: {{ entity.attributes.party }}
      </p>
    </div>
  </div>
</template>

<script>
export default {
  data() {
    return {
      query: '',
      entities: [],
      loading: false
    };
  },
  methods: {
    async searchEntities() {
      this.loading = true;
      try {
        const response = await fetch(
          `https://nes.jawafdehi.org/api/entities?query=${encodeURIComponent(this.query)}`
        );
        const data = await response.json();
        this.entities = data.entities;
      } catch (error) {
        console.error('Error fetching entities:', error);
      } finally {
        this.loading = false;
      }
    }
  }
};
</script>
```

## Data Analysis Examples

### Analyze Political Party Distribution

Analyze the distribution of politicians across parties:

```python
import requests
from collections import Counter

# Get all persons
response = requests.get(
    "https://nes.jawafdehi.org/api/entities",
    params={"entity_type": "person", "limit": 1000}
)

entities = response.json()['entities']

# Count party affiliations
party_counts = Counter()
for entity in entities:
    party = entity['attributes'].get('party')
    if party:
        party_counts[party] += 1

# Print results
print("Political Party Distribution:")
for party, count in party_counts.most_common():
    print(f"  {party}: {count} members")
```

### Generate Entity Report

Create a comprehensive report for an entity:

```python
import requests
from datetime import datetime

def generate_entity_report(entity_id):
    """Generate a comprehensive report for an entity."""
    
    # Get entity details
    entity_response = requests.get(f"https://nes.jawafdehi.org/api/entities/{entity_id}")
    entity = entity_response.json()
    
    # Get relationships
    rel_response = requests.get(
        f"https://nes.jawafdehi.org/api/entities/{entity_id}/relationships"
    )
    relationships = rel_response.json()['relationships']
    
    # Get version history
    version_response = requests.get(
        f"https://nes.jawafdehi.org/api/entities/{entity_id}/versions"
    )
    versions = version_response.json()['versions']
    
    # Generate report
    print("=" * 60)
    print(f"ENTITY REPORT: {entity['names'][0]['en']['full']}")
    print("=" * 60)
    
    print(f"\nID: {entity['id']}")
    print(f"Type: {entity['type']}")
    if entity.get('sub_type'):
        print(f"Subtype: {entity['sub_type']}")
    
    print("\nNames:")
    for name in entity['names']:
        print(f"  {name['kind']}: {name['en']['full']}")
        if name.get('ne'):
            print(f"    Nepali: {name['ne']['full']}")
    
    print("\nAttributes:")
    for key, value in entity['attributes'].items():
        print(f"  {key}: {value}")
    
    print(f"\nRelationships ({len(relationships)}):")
    for rel in relationships[:5]:  # Show first 5
        target_response = requests.get(
            f"https://nes.jawafdehi.org/api/entities/{rel['target_entity_id']}"
        )
        target = target_response.json()
        target_name = target['names'][0]['en']['full']
        print(f"  {rel['type']} → {target_name}")
    
    print(f"\nVersion History ({len(versions)} versions):")
    for version in versions[:3]:  # Show first 3
        created_at = datetime.fromisoformat(version['created_at'].replace('Z', '+00:00'))
        print(f"  v{version['version_number']}: {created_at.strftime('%Y-%m-%d')} - {version.get('change_description', 'No description')}")
    
    print("\n" + "=" * 60)

# Generate report
generate_entity_report("entity:person/ram-chandra-poudel")
```

## Error Handling

### Robust Error Handling

Handle API errors gracefully:

```python
import requests

def safe_api_call(url, params=None):
    """Make an API call with proper error handling."""
    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()  # Raise exception for 4xx/5xx status codes
        return response.json()
    
    except requests.exceptions.Timeout:
        print("Error: Request timed out")
        return None
    
    except requests.exceptions.ConnectionError:
        print("Error: Could not connect to API")
        return None
    
    except requests.exceptions.HTTPError as e:
        if response.status_code == 404:
            print("Error: Entity not found")
        elif response.status_code == 400:
            error_data = response.json()
            print(f"Error: {error_data['error']['message']}")
        else:
            print(f"Error: HTTP {response.status_code}")
        return None
    
    except Exception as e:
        print(f"Unexpected error: {e}")
        return None

# Use it
data = safe_api_call(
    "https://nes.jawafdehi.org/api/entities",
    params={"query": "poudel"}
)

if data:
    print(f"Found {data['total']} results")
```

## Next Steps

- [API Reference](/docs) - Interactive OpenAPI documentation
- [Data Models](/consumers/data-models) - Understanding entity schemas
- [Getting Started](/consumers/getting-started) - Basic usage guide
- [Service Design](/specs/nepal-entity-service/design) - System design overview
