# Monitoring Rejected/Refused Connections - Analysis

## Is It Possible?

**Short answer: Yes, but with limitations.**

### Current Situation

1. **Flow-based monitoring (what we're doing now):**
   - Only sees flows that are **successfully established** or **partially established**
   - When ACL rules DENY traffic, Floodlight may:
     - Create a flow entry with DENY action (best case - we can see it)
     - Drop the packet before creating a flow (worst case - invisible to flow monitoring)
   - Connection refused (no service listening) might create a flow entry, but it depends

2. **Port statistics (alternative approach):**
   - Port statistics show **all packets** that pass through a switch port
   - This includes:
     - ✅ Successful connections
     - ✅ Denied/blocked packets (if they reach the switch)
     - ✅ Connection attempts (SYN packets)
     - ❌ But doesn't tell us destination port or protocol easily

3. **Device/Flow statistics:**
   - Can track connection attempts if flows are created
   - But ACL DENY rules might prevent flow creation

## Is It Efficient?

### Flow-based (Current):
- ✅ **Efficient**: Only queries flow tables (already doing this)
- ✅ **Detailed**: Gets source IP, destination port, protocol
- ❌ **Limited**: May miss denied connections

### Port Statistics-based:
- ⚠️ **Moderate efficiency**: Need to query all switch ports
- ⚠️ **Less detailed**: Hard to identify which protocol/port was targeted
- ✅ **More comprehensive**: Catches all traffic including denied

### Hybrid Approach (Best):
- Use flows for detailed analysis (current)
- Use port statistics as backup to detect anomalies
- Track connection attempts by monitoring SYN packets in flows

## Does It Make Sense?

**Yes, absolutely!** From a security perspective:

1. **Attempted connections to blocked ports are suspicious** - even if they fail
2. **Port scanning detection** - multiple failed connection attempts
3. **Intrusion detection** - attackers often probe before attacking
4. **Compliance** - need to log all security-relevant events

## Recommended Solution

### Option 1: Enhanced Flow Monitoring (Recommended)
**What to do:**
- Monitor flows that target blocked protocol ports (destination port 22, 21, 3389, etc.)
- Even if the connection fails, the flow entry might exist with low packet count
- Check for flows with destination ports matching blocked protocols

**Pros:**
- Efficient (already querying flows)
- Detailed (know exactly which protocol was targeted)
- Works with existing code structure

**Cons:**
- Might miss some denied connections if ACL prevents flow creation

### Option 2: Port Statistics Tracking
**What to do:**
- Track port statistics over time
- Detect sudden spikes in traffic from specific IPs
- Correlate with known blocked protocol ports

**Pros:**
- Catches all traffic including denied
- More comprehensive

**Cons:**
- Less efficient (more data to process)
- Harder to identify specific protocols
- More complex to implement

### Option 3: Hybrid Approach
**What to do:**
- Primary: Enhanced flow monitoring (check for flows to blocked ports)
- Secondary: Port statistics for anomaly detection
- Track connection attempts (SYN packets) specifically

**Pros:**
- Best of both worlds
- Comprehensive coverage

**Cons:**
- More complex
- Higher resource usage

## My Recommendation

**Go with Option 1 (Enhanced Flow Monitoring)** because:

1. **It's the most practical**: We're already querying flows efficiently
2. **It provides the detail we need**: We can see destination ports and protocols
3. **It works for most cases**: Even if connections are refused, flow entries are often created
4. **It's efficient**: Minimal additional overhead

### Implementation Strategy:

1. **Check flows for destination ports matching blocked protocols** - even if packet count is low
2. **Track connection attempts** - flows with destination ports 22, 21, 3389, etc. from guest/employee roles
3. **Alert on any attempt** - not just successful connections

This way, when someone tries `ssh user@10.0.0.2`:
- The SYN packet creates a flow entry (or should)
- We detect the flow with destination port 22
- We see it's from a "guest" role (SSH is blocked)
- We trigger an alert **even if the connection is refused**

## Testing

To verify this works:
1. Try SSH connection (will be refused)
2. Check if a flow entry is created in Floodlight
3. If yes, our monitoring will catch it
4. If no, we might need to add port statistics as backup

