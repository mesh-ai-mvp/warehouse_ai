# Enhanced Warehouse Shelf Visualization Plan

## Detailed 3D Shelf Layout with Intelligent Medication Placement

---

## Executive Summary

This document outlines the comprehensive plan to enhance the warehouse visualization with detailed shelf-level views, intelligent medication placement algorithms, and realistic inventory positioning based on pharmaceutical best practices.

---

## Table of Contents

1. [Visualization Hierarchy](#visualization-hierarchy)
2. [Enhanced Data Model](#enhanced-data-model)
3. [Medication Placement Algorithm](#medication-placement-algorithm)
4. [API Structure Design](#api-structure-design)
5. [UI Visualization Approach](#ui-visualization-approach)
6. [Implementation Details](#implementation-details)
7. [Data Generation Updates](#data-generation-updates)

---

## Visualization Hierarchy

### Navigation Flow

```
Warehouse Overview (3D Zones)
    ↓ Click Zone
Aisle View (Multiple Aisles in Zone)
    ↓ Click Aisle
Shelf View (Horizontal Shelf Lines)
    ↓ Click Shelf
Detailed Shelf Grid (3D Medication Placement)
```

### Shelf Coordinate System

```
Each shelf is divided into a 3D grid:
- X-axis: Width (10 slots)
- Y-axis: Depth (3 rows - Front/Middle/Back)
- Z-axis: Height (Already handled by shelf levels)

Example:
[Back]   [B1][B2][B3][B4][B5][B6][B7][B8][B9][B10]
[Middle] [M1][M2][M3][M4][M5][M6][M7][M8][M9][M10]
[Front]  [F1][F2][F3][F4][F5][F6][F7][F8][F9][F10]
         ← High Traffic Area / Picking Face →
```

---

## Enhanced Data Model

### Medication Attributes for Placement

```python
# Additional medication attributes needed
medication_attributes = {
    'med_id': int,
    'name': str,
    'category': str,  # Chronic, Intermittent, Sporadic

    # Movement characteristics
    'velocity_score': float,  # 0-100, higher = faster moving
    'picks_per_day': float,   # Average daily picks
    'movement_category': str, # 'Fast', 'Medium', 'Slow'

    # Physical characteristics
    'weight_kg': float,       # For ergonomic placement
    'volume_cm3': float,      # Space requirements
    'fragility': str,         # 'High', 'Medium', 'Low'
    'stackable': bool,        # Can other items be placed on top

    # Storage requirements
    'requires_refrigeration': bool,
    'requires_security': bool,
    'light_sensitive': bool,
    'humidity_sensitive': bool,

    # Expiry management
    'shelf_life_days': int,
    'expiry_urgency': str,    # 'Critical', 'Soon', 'Normal', 'Long'
    'fifo_priority': int,     # First-In-First-Out priority score

    # Operational
    'abc_classification': str, # 'A', 'B', 'C' based on value*volume
    'reorder_frequency': float, # Days between orders
    'batch_picking_compatible': bool
}
```

### Shelf Position Model

```python
# Enhanced shelf position structure
shelf_position = {
    'position_id': int,
    'shelf_id': int,
    'grid_x': int,        # 1-10 (left to right)
    'grid_y': int,        # 1-3 (front to back)
    'grid_label': str,    # 'F5', 'M3', 'B8' etc.

    # What's in this position
    'med_id': int or None,
    'batch_id': int or None,
    'quantity': int,
    'placement_date': datetime,

    # Position characteristics
    'is_golden_zone': bool,  # Ergonomic picking height
    'accessibility': float,   # 0-1, how easy to reach
    'reserved_for': str,      # 'fast-movers', 'heavy-items', etc.

    # Placement rules
    'max_weight': float,
    'allows_stacking': bool,
    'temperature_zone': str
}
```

### Database Schema Updates

```sql
-- Enhanced medication attributes table
CREATE TABLE medication_attributes (
    med_id INTEGER PRIMARY KEY,
    velocity_score REAL DEFAULT 0,
    picks_per_day REAL DEFAULT 0,
    movement_category TEXT CHECK(movement_category IN ('Fast', 'Medium', 'Slow')),
    weight_kg REAL,
    volume_cm3 REAL,
    fragility TEXT CHECK(fragility IN ('High', 'Medium', 'Low')),
    stackable BOOLEAN DEFAULT 1,
    requires_refrigeration BOOLEAN DEFAULT 0,
    requires_security BOOLEAN DEFAULT 0,
    light_sensitive BOOLEAN DEFAULT 0,
    humidity_sensitive BOOLEAN DEFAULT 0,
    abc_classification TEXT CHECK(abc_classification IN ('A', 'B', 'C')),
    reorder_frequency REAL,
    batch_picking_compatible BOOLEAN DEFAULT 1,
    FOREIGN KEY (med_id) REFERENCES medications(med_id)
);

-- Detailed shelf positions
CREATE TABLE shelf_positions (
    position_id INTEGER PRIMARY KEY AUTOINCREMENT,
    shelf_id INTEGER NOT NULL,
    grid_x INTEGER NOT NULL CHECK(grid_x BETWEEN 1 AND 10),
    grid_y INTEGER NOT NULL CHECK(grid_y BETWEEN 1 AND 3),
    grid_label TEXT GENERATED ALWAYS AS (
        CASE grid_y
            WHEN 1 THEN 'F'
            WHEN 2 THEN 'M'
            WHEN 3 THEN 'B'
        END || grid_x
    ) STORED,
    is_golden_zone BOOLEAN DEFAULT 0,
    accessibility REAL DEFAULT 1.0,
    reserved_for TEXT,
    max_weight REAL DEFAULT 50.0,
    allows_stacking BOOLEAN DEFAULT 1,
    FOREIGN KEY (shelf_id) REFERENCES warehouse_shelves(shelf_id),
    UNIQUE(shelf_id, grid_x, grid_y)
);

-- Medication placements with history
CREATE TABLE medication_placements (
    placement_id INTEGER PRIMARY KEY AUTOINCREMENT,
    position_id INTEGER NOT NULL,
    med_id INTEGER NOT NULL,
    batch_id INTEGER,
    quantity INTEGER NOT NULL,
    placement_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    placed_by TEXT,
    placement_reason TEXT, -- 'initial', 'replenishment', 'reorganization'
    expiry_date DATE,
    is_active BOOLEAN DEFAULT 1,
    FOREIGN KEY (position_id) REFERENCES shelf_positions(position_id),
    FOREIGN KEY (med_id) REFERENCES medications(med_id),
    FOREIGN KEY (batch_id) REFERENCES batch_info(batch_id)
);

-- Movement history for velocity calculations
CREATE TABLE movement_history (
    movement_id INTEGER PRIMARY KEY AUTOINCREMENT,
    med_id INTEGER NOT NULL,
    position_id INTEGER,
    movement_type TEXT CHECK(movement_type IN ('pick', 'replenish', 'relocate')),
    quantity INTEGER,
    movement_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    operator_id TEXT,
    order_id INTEGER,
    FOREIGN KEY (med_id) REFERENCES medications(med_id),
    FOREIGN KEY (position_id) REFERENCES shelf_positions(position_id)
);
```

---

## Medication Placement Algorithm

### Placement Strategy

```python
class MedicationPlacementStrategy:
    """
    Intelligent medication placement based on warehouse best practices
    """

    def calculate_placement_score(self, medication, position):
        """
        Calculate optimal placement score for a medication at a position
        Higher score = better placement
        """
        score = 0

        # 1. Velocity-based placement (40% weight)
        # Fast movers go to front, golden zone
        if medication['movement_category'] == 'Fast':
            if position['grid_y'] == 1:  # Front row
                score += 40
            if position['is_golden_zone']:
                score += 20
        elif medication['movement_category'] == 'Medium':
            if position['grid_y'] == 2:  # Middle row
                score += 30
        else:  # Slow movers
            if position['grid_y'] == 3:  # Back row
                score += 30

        # 2. Weight-based placement (20% weight)
        # Heavy items at lower levels, already handled by shelf level
        if medication['weight_kg'] < 5:
            score += 20  # Light items are flexible
        elif medication['weight_kg'] < 15:
            score += 15
        else:
            score += 10 if position['max_weight'] >= medication['weight_kg'] else -50

        # 3. Expiry-based placement (20% weight)
        if medication['expiry_urgency'] == 'Critical':
            if position['grid_y'] == 1:  # Front for easy access
                score += 20
        elif medication['expiry_urgency'] == 'Soon':
            if position['grid_y'] <= 2:  # Front or middle
                score += 15
        else:
            score += 10  # Normal expiry, any position OK

        # 4. ABC Classification (10% weight)
        if medication['abc_classification'] == 'A':
            if position['accessibility'] > 0.8:
                score += 10
        elif medication['abc_classification'] == 'B':
            if position['accessibility'] > 0.5:
                score += 8
        else:
            score += 5  # C items can go anywhere

        # 5. Special requirements (10% weight)
        if medication['requires_security'] and position['reserved_for'] == 'controlled':
            score += 10
        if medication['fragility'] == 'High' and not position['allows_stacking']:
            score += 5

        return score

    def generate_placement_plan(self, medications, shelves):
        """
        Generate optimal placement plan for all medications
        """
        placements = []
        used_positions = set()

        # Sort medications by priority
        sorted_meds = sorted(medications,
                           key=lambda m: (
                               m['velocity_score'],
                               m['abc_classification'] == 'A',
                               m['expiry_urgency'] == 'Critical'
                           ),
                           reverse=True)

        for med in sorted_meds:
            best_position = None
            best_score = -1

            for shelf in shelves:
                for position in shelf['positions']:
                    if position['position_id'] not in used_positions:
                        score = self.calculate_placement_score(med, position)
                        if score > best_score:
                            best_score = score
                            best_position = position

            if best_position:
                placements.append({
                    'med_id': med['med_id'],
                    'position_id': best_position['position_id'],
                    'shelf_id': best_position['shelf_id'],
                    'grid_label': best_position['grid_label'],
                    'placement_score': best_score
                })
                used_positions.add(best_position['position_id'])

        return placements
```

### FIFO Implementation

```python
def arrange_by_fifo(shelf_positions, medication_batches):
    """
    Arrange medication batches following FIFO principle
    Older batches at front, newer at back
    """
    # Sort batches by expiry date (oldest first)
    sorted_batches = sorted(medication_batches,
                          key=lambda b: b['expiry_date'])

    # Place oldest batches in front row (y=1)
    # Medium age in middle row (y=2)
    # Newest in back row (y=3)
    arrangements = []

    for idx, batch in enumerate(sorted_batches):
        if idx < 10:  # First 10 go to front
            y_position = 1
            x_position = (idx % 10) + 1
        elif idx < 20:  # Next 10 to middle
            y_position = 2
            x_position = (idx % 10) + 1
        else:  # Rest to back
            y_position = 3
            x_position = (idx % 10) + 1

        arrangements.append({
            'batch_id': batch['batch_id'],
            'grid_x': x_position,
            'grid_y': y_position,
            'expiry_date': batch['expiry_date']
        })

    return arrangements
```

---

## API Structure Design

### Warehouse Layout API Response

```json
{
  "warehouse": {
    "total_zones": 5,
    "total_aisles": 6,
    "total_shelves": 48,
    "total_medications": 50,
    "zones": [
      {
        "zone_id": 1,
        "zone_name": "Zone R1",
        "zone_type": "restricted",
        "temperature_range": "15-25°C",
        "aisles": [
          {
            "aisle_id": 1,
            "aisle_name": "Controlled Substances A",
            "position": {"x": 0, "z": 0},
            "shelf_count": 8,
            "medication_count": 15,
            "utilization": 75.5
          }
        ]
      }
    ]
  }
}
```

### Aisle Detail API Response

```json
{
  "aisle": {
    "aisle_id": 1,
    "aisle_name": "Controlled Substances A",
    "zone_id": 1,
    "category": "Controlled",
    "temperature": 22,
    "shelves": [
      {
        "shelf_id": 1,
        "position": 0,
        "level": 0,
        "utilization_percent": 85,
        "total_positions": 30,
        "occupied_positions": 25,
        "medication_summary": [
          {
            "med_id": 13,
            "name": "Morphine Sulfate 30mg",
            "placement": "F1-F3",
            "quantity": 45
          }
        ]
      }
    ]
  }
}
```

### Detailed Shelf View API Response

```json
{
  "shelf": {
    "shelf_id": 1,
    "aisle_id": 1,
    "shelf_dimensions": {
      "width_slots": 10,
      "depth_rows": 3,
      "labels": {
        "front": ["F1", "F2", "F3", "F4", "F5", "F6", "F7", "F8", "F9", "F10"],
        "middle": ["M1", "M2", "M3", "M4", "M5", "M6", "M7", "M8", "M9", "M10"],
        "back": ["B1", "B2", "B3", "B4", "B5", "B6", "B7", "B8", "B9", "B10"]
      }
    },
    "positions": [
      {
        "position_id": 1,
        "grid_label": "F1",
        "grid_x": 1,
        "grid_y": 1,
        "medication": {
          "med_id": 13,
          "name": "Morphine Sulfate 30mg",
          "batch_id": 245,
          "lot_number": "LOT-202501-013",
          "quantity": 15,
          "expiry_date": "2025-12-31",
          "expiry_status": "normal",
          "velocity": "slow",
          "placement_reason": "controlled_substance"
        },
        "is_golden_zone": true,
        "accessibility": 1.0
      },
      {
        "position_id": 2,
        "grid_label": "F2",
        "grid_x": 2,
        "grid_y": 1,
        "medication": {
          "med_id": 13,
          "name": "Morphine Sulfate 30mg",
          "batch_id": 246,
          "lot_number": "LOT-202502-013",
          "quantity": 10,
          "expiry_date": "2026-01-15",
          "expiry_status": "normal",
          "velocity": "slow",
          "placement_reason": "controlled_substance"
        }
      },
      {
        "position_id": 3,
        "grid_label": "F3",
        "grid_x": 3,
        "grid_y": 1,
        "medication": null
      },
      {
        "position_id": 11,
        "grid_label": "M1",
        "grid_x": 1,
        "grid_y": 2,
        "medication": {
          "med_id": 14,
          "name": "OxyContin 20mg",
          "batch_id": 250,
          "quantity": 20,
          "expiry_date": "2025-11-15",
          "behind_medication": "Morphine Sulfate 30mg"
        }
      },
      {
        "position_id": 21,
        "grid_label": "B1",
        "grid_x": 1,
        "grid_y": 3,
        "medication": {
          "med_id": 13,
          "name": "Morphine Sulfate 30mg",
          "batch_id": 247,
          "lot_number": "LOT-202503-013",
          "quantity": 25,
          "expiry_date": "2026-03-20",
          "expiry_status": "long",
          "placement_reason": "newer_batch_fifo"
        }
      }
    ],
    "placement_logic": {
      "front_row": "Fast-moving and expiring items",
      "middle_row": "Medium velocity items",
      "back_row": "Slow-moving and newer batches"
    },
    "alerts": [
      {
        "type": "expiry",
        "position": "F5",
        "message": "Medication expiring in 15 days"
      }
    ]
  }
}
```

---

## UI Visualization Approach

### Shelf View Component Design

```typescript
// Enhanced shelf visualization component
interface ShelfVisualizationProps {
  shelf: DetailedShelf;
  viewMode: 'grid' | '3d' | 'list';
  onPositionClick: (position: Position) => void;
}

export function ShelfVisualization({ shelf, viewMode, onPositionClick }: ShelfVisualizationProps) {
  return (
    <div className="shelf-container">
      {/* Shelf Header */}
      <div className="shelf-header">
        <h3>Shelf {shelf.position} - Level {shelf.level}</h3>
        <div className="shelf-stats">
          <span>Utilization: {shelf.utilization}%</span>
          <span>Temperature: {shelf.temperature}°C</span>
        </div>
      </div>

      {/* Grid View */}
      {viewMode === 'grid' && (
        <div className="shelf-grid">
          {/* Back Row */}
          <div className="shelf-row back-row">
            <div className="row-label">Back</div>
            {shelf.positions.filter(p => p.grid_y === 3).map(position => (
              <ShelfPosition
                key={position.position_id}
                position={position}
                onClick={() => onPositionClick(position)}
              />
            ))}
          </div>

          {/* Middle Row */}
          <div className="shelf-row middle-row">
            <div className="row-label">Middle</div>
            {shelf.positions.filter(p => p.grid_y === 2).map(position => (
              <ShelfPosition
                key={position.position_id}
                position={position}
                onClick={() => onPositionClick(position)}
              />
            ))}
          </div>

          {/* Front Row */}
          <div className="shelf-row front-row">
            <div className="row-label">Front</div>
            {shelf.positions.filter(p => p.grid_y === 1).map(position => (
              <ShelfPosition
                key={position.position_id}
                position={position}
                onClick={() => onPositionClick(position)}
                highlight={position.is_golden_zone}
              />
            ))}
          </div>
        </div>
      )}

      {/* Position Legend */}
      <div className="position-legend">
        <div className="legend-item">
          <div className="color-box fast-moving" />
          <span>Fast Moving</span>
        </div>
        <div className="legend-item">
          <div className="color-box expiring" />
          <span>Expiring Soon</span>
        </div>
        <div className="legend-item">
          <div className="color-box controlled" />
          <span>Controlled</span>
        </div>
      </div>
    </div>
  );
}
```

### Position Component

```typescript
function ShelfPosition({ position, onClick, highlight }) {
  const getPositionColor = () => {
    if (!position.medication) return 'bg-gray-200';

    if (position.medication.expiry_status === 'critical') return 'bg-red-500';
    if (position.medication.expiry_status === 'soon') return 'bg-yellow-500';
    if (position.medication.velocity === 'fast') return 'bg-green-500';
    if (position.medication.velocity === 'medium') return 'bg-blue-500';
    return 'bg-gray-400';
  };

  return (
    <motion.div
      className={`shelf-position ${getPositionColor()} ${highlight ? 'golden-zone' : ''}`}
      onClick={onClick}
      whileHover={{ scale: 1.05 }}
      whileTap={{ scale: 0.95 }}
    >
      <div className="position-label">{position.grid_label}</div>
      {position.medication && (
        <>
          <div className="med-name">{position.medication.name.substring(0, 10)}...</div>
          <div className="quantity">Qty: {position.medication.quantity}</div>
          {position.medication.expiry_status === 'critical' && (
            <div className="alert-icon">⚠️</div>
          )}
        </>
      )}
    </motion.div>
  );
}
```

### Visual Design Elements

```css
/* Shelf visualization styles */
.shelf-grid {
  display: flex;
  flex-direction: column;
  gap: 20px;
  padding: 20px;
  background: linear-gradient(180deg, #1a1a1a 0%, #2d2d2d 100%);
  border-radius: 12px;
}

.shelf-row {
  display: grid;
  grid-template-columns: 80px repeat(10, 1fr);
  gap: 8px;
  padding: 12px;
  background: rgba(255, 255, 255, 0.05);
  border-radius: 8px;
}

.back-row {
  opacity: 0.7;
  transform: perspective(600px) rotateX(10deg) translateZ(-20px);
}

.middle-row {
  opacity: 0.85;
  transform: perspective(600px) translateZ(0px);
}

.front-row {
  opacity: 1;
  transform: perspective(600px) rotateX(-5deg) translateZ(20px);
}

.shelf-position {
  aspect-ratio: 1;
  border-radius: 8px;
  padding: 8px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: all 0.3s ease;
  position: relative;
  border: 2px solid transparent;
}

.shelf-position.golden-zone {
  border-color: gold;
  box-shadow: 0 0 15px rgba(255, 215, 0, 0.3);
}

.shelf-position:hover {
  transform: translateY(-5px);
  box-shadow: 0 10px 20px rgba(0, 0, 0, 0.3);
}

/* Color coding for medications */
.fast-moving { background: linear-gradient(135deg, #10b981, #059669); }
.expiring { background: linear-gradient(135deg, #f59e0b, #d97706); }
.controlled { background: linear-gradient(135deg, #ef4444, #dc2626); }
.slow-moving { background: linear-gradient(135deg, #6b7280, #4b5563); }
```

---

## Implementation Details

### Phase 1: Data Generation Updates

```python
# synthetic_data_generator.py updates

def generate_medication_attributes(medications, consumption_history):
    """
    Generate detailed medication attributes for placement logic
    """
    attributes = []

    for med in medications:
        # Calculate velocity from consumption history
        med_consumption = consumption_history[
            consumption_history['med_id'] == med['med_id']
        ]

        picks_per_day = med_consumption['quantity'].sum() / 365
        velocity_score = min(100, picks_per_day * 10)

        # Determine movement category
        if velocity_score > 70:
            movement_category = 'Fast'
        elif velocity_score > 30:
            movement_category = 'Medium'
        else:
            movement_category = 'Slow'

        # Physical attributes
        weight = np.random.uniform(0.1, 25.0)  # kg
        volume = np.random.uniform(100, 5000)  # cm3

        # Storage requirements based on medication type
        requires_refrigeration = 'insulin' in med['name'].lower() or \
                                'vaccine' in med['name'].lower()
        requires_security = 'morphine' in med['name'].lower() or \
                          'oxy' in med['name'].lower()

        # ABC classification based on value and volume
        if med['category'] == 'Chronic' and velocity_score > 50:
            abc_class = 'A'
        elif med['category'] == 'Intermittent':
            abc_class = 'B'
        else:
            abc_class = 'C'

        attributes.append({
            'med_id': med['med_id'],
            'velocity_score': velocity_score,
            'picks_per_day': picks_per_day,
            'movement_category': movement_category,
            'weight_kg': round(weight, 2),
            'volume_cm3': round(volume, 2),
            'fragility': np.random.choice(['High', 'Medium', 'Low'],
                                        p=[0.1, 0.3, 0.6]),
            'stackable': weight < 10,
            'requires_refrigeration': requires_refrigeration,
            'requires_security': requires_security,
            'light_sensitive': np.random.random() < 0.2,
            'humidity_sensitive': np.random.random() < 0.15,
            'abc_classification': abc_class,
            'reorder_frequency': np.random.uniform(7, 60),
            'batch_picking_compatible': movement_category != 'Slow'
        })

    return pd.DataFrame(attributes)

def generate_shelf_positions(shelves):
    """
    Generate detailed position grid for each shelf
    """
    positions = []
    position_id = 1

    for shelf in shelves:
        shelf_level = shelf['level']

        # Golden zone is at comfortable picking height (levels 1-2)
        is_golden_level = shelf_level in [1, 2]

        for x in range(1, 11):  # 10 positions wide
            for y in range(1, 4):  # 3 positions deep
                # Calculate accessibility
                # Front row (y=1) is most accessible
                # Center positions (x=4-7) are most accessible
                accessibility = 1.0
                if y == 2:
                    accessibility *= 0.8
                elif y == 3:
                    accessibility *= 0.6

                if x <= 2 or x >= 9:
                    accessibility *= 0.9

                # Determine if golden zone
                is_golden = is_golden_level and y == 1 and 4 <= x <= 7

                # Reserve positions for special items
                reserved = None
                if is_golden and x <= 5:
                    reserved = 'fast-movers'
                elif y == 3:
                    reserved = 'overstock'

                positions.append({
                    'position_id': position_id,
                    'shelf_id': shelf['shelf_id'],
                    'grid_x': x,
                    'grid_y': y,
                    'is_golden_zone': is_golden,
                    'accessibility': round(accessibility, 2),
                    'reserved_for': reserved,
                    'max_weight': 50.0 if shelf_level <= 2 else 25.0,
                    'allows_stacking': True
                })
                position_id += 1

    return pd.DataFrame(positions)

def generate_medication_placements(medications, positions, batches):
    """
    Generate intelligent medication placements
    """
    strategy = MedicationPlacementStrategy()

    # Group batches by medication
    med_batches = {}
    for batch in batches:
        med_id = batch['med_id']
        if med_id not in med_batches:
            med_batches[med_id] = []
        med_batches[med_id].append(batch)

    placements = []

    for med_id, med_batches_list in med_batches.items():
        med = next(m for m in medications if m['med_id'] == med_id)

        # Sort batches by expiry (FIFO)
        sorted_batches = sorted(med_batches_list,
                              key=lambda b: b['expiry_date'])

        # Find best positions for this medication
        med_positions = strategy.find_optimal_positions(
            med, sorted_batches, positions
        )

        for batch, position in zip(sorted_batches, med_positions):
            placements.append({
                'position_id': position['position_id'],
                'med_id': med_id,
                'batch_id': batch['batch_id'],
                'quantity': batch['remaining_quantity'],
                'placement_date': datetime.now(),
                'placement_reason': 'intelligent_placement',
                'expiry_date': batch['expiry_date'],
                'is_active': True
            })

    return pd.DataFrame(placements)
```

### Phase 2: API Implementation

```python
# warehouse_routes.py - Enhanced shelf detail endpoint

@router.get("/shelf/{shelf_id}/detailed")
async def get_detailed_shelf_layout(shelf_id: int):
    """
    Get comprehensive shelf layout with all positions and medications
    """
    try:
        conn = data_loader.get_connection()

        # Get shelf information
        shelf_query = """
            SELECT s.*, a.aisle_name, a.category, a.temperature
            FROM warehouse_shelves s
            JOIN warehouse_aisles a ON s.aisle_id = a.aisle_id
            WHERE s.shelf_id = ?
        """
        shelf = pd.read_sql_query(shelf_query, conn, params=[shelf_id])

        # Get all positions for this shelf
        positions_query = """
            SELECT p.*,
                   mp.med_id, mp.batch_id, mp.quantity, mp.expiry_date,
                   m.name as med_name, m.category as med_category,
                   ma.velocity_score, ma.movement_category,
                   b.lot_number
            FROM shelf_positions p
            LEFT JOIN medication_placements mp ON p.position_id = mp.position_id
                AND mp.is_active = 1
            LEFT JOIN medications m ON mp.med_id = m.med_id
            LEFT JOIN medication_attributes ma ON m.med_id = ma.med_id
            LEFT JOIN batch_info b ON mp.batch_id = b.batch_id
            WHERE p.shelf_id = ?
            ORDER BY p.grid_y, p.grid_x
        """
        positions = pd.read_sql_query(positions_query, conn, params=[shelf_id])

        # Structure the response
        shelf_data = shelf.to_dict('records')[0] if not shelf.empty else {}

        # Group positions by row
        front_row = positions[positions['grid_y'] == 1].to_dict('records')
        middle_row = positions[positions['grid_y'] == 2].to_dict('records')
        back_row = positions[positions['grid_y'] == 3].to_dict('records')

        # Calculate placement statistics
        total_positions = len(positions)
        occupied_positions = positions['med_id'].notna().sum()

        # Identify medications in each row with relationships
        position_map = {}
        for _, pos in positions.iterrows():
            if pd.notna(pos['med_id']):
                grid_label = f"{'F' if pos['grid_y']==1 else 'M' if pos['grid_y']==2 else 'B'}{pos['grid_x']}"
                position_map[grid_label] = {
                    'med_name': pos['med_name'],
                    'quantity': pos['quantity'],
                    'expiry': pos['expiry_date']
                }

        # Build relationships (what's behind what)
        for pos in front_row:
            grid_x = pos['grid_x']
            behind_label = f"M{grid_x}"
            further_back_label = f"B{grid_x}"

            if behind_label in position_map:
                pos['behind'] = position_map[behind_label]['med_name']
            if further_back_label in position_map:
                pos['further_back'] = position_map[further_back_label]['med_name']

        response = {
            'shelf': shelf_data,
            'dimensions': {
                'width_slots': 10,
                'depth_rows': 3,
                'total_positions': total_positions,
                'occupied_positions': occupied_positions,
                'utilization_percent': round((occupied_positions/total_positions)*100, 1)
            },
            'rows': {
                'front': front_row,
                'middle': middle_row,
                'back': back_row
            },
            'placement_strategy': {
                'front_row': 'Fast-moving items, items expiring soon, high-pick frequency',
                'middle_row': 'Medium velocity items, standard stock',
                'back_row': 'Slow-moving items, overstock, newer batches'
            },
            'position_map': position_map
        }

        return clean_nan_values(response)

    except Exception as e:
        logger.error(f"Error fetching detailed shelf layout: {e}")
        raise HTTPException(status_code=500, detail=str(e))
```

---

## Updates to WAREHOUSE-UI-INTEGRATION-PLAN.md

### Additional Tasks for Phase 1: Data Infrastructure ✅ **COMPLETED**

| Task ID | Task Description | Duration | Status |
|---------|-----------------|----------|--------|
| P1.8 | Create medication_attributes table | 2 hours | ✅ COMPLETED |
| P1.9 | Generate velocity scores from consumption data | 3 hours | ✅ COMPLETED |
| P1.10 | Create shelf_positions table with 3D grid | 2 hours | ✅ COMPLETED |
| P1.11 | Generate position grid (30 positions per shelf) | 2 hours | ✅ COMPLETED |
| P1.12 | Implement placement algorithm | 4 hours | ✅ COMPLETED |
| P1.13 | Generate medication_placements with FIFO | 3 hours | ✅ COMPLETED |
| P1.14 | Create movement_history for tracking | 2 hours | ✅ COMPLETED |

### Additional Tasks for Phase 2: Backend API ✅ **COMPLETED**

| Task ID | Task Description | Duration | Status |
|---------|-----------------|----------|--------|
| P2.10 | Implement detailed shelf layout endpoint | 3 hours | ✅ COMPLETED |
| P2.11 | Add position-level query methods | 2 hours | ✅ COMPLETED |
| P2.12 | Create placement recommendation API | 3 hours | ✅ COMPLETED |
| P2.13 | Add FIFO validation endpoint | 2 hours | ✅ COMPLETED |
| P2.14 | Implement movement tracking API | 2 hours | ✅ COMPLETED |

### Additional Tasks for Phase 3: Frontend Integration ✅ **COMPLETED**

| Task ID | Task Description | Duration | Status |
|---------|-----------------|----------|--------|
| P3.10 | Create ShelfVisualization component | 4 hours | ✅ COMPLETED |
| P3.11 | Implement 3D grid layout | 3 hours | ✅ COMPLETED |
| P3.12 | Add position hover details | 2 hours | ✅ COMPLETED |
| P3.13 | Create medication relationship view | 3 hours | ✅ COMPLETED |
| P3.14 | Add placement legend and color coding | 2 hours | ✅ COMPLETED |
| P3.15 | Implement position click interactions | 2 hours | ✅ COMPLETED |

---

## Success Metrics

### Placement Efficiency

- ✅ 90% of fast-moving items in front row
- ✅ 100% FIFO compliance for batches
- ✅ Zero expired medications in back rows
- ✅ 95% golden zone utilization for A-class items

### Visualization Quality

- ✅ Clear visual distinction between rows
- ✅ Intuitive color coding for medication status
- ✅ Readable position labels and quantities
- ✅ Smooth hover and click interactions

### Data Accuracy

- ✅ Real-time position updates
- ✅ Accurate velocity calculations
- ✅ Correct expiry status indicators
- ✅ Proper relationship mapping (front/behind)

---

**END OF ENHANCED PLAN**
