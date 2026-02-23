using UnityEngine;

/// <summary>
/// Simulates object detection on the pin grid using 3 discrete height levels:
///   Level -1 (BELOW)  : pin retracts below the reference / cover surface
///   Level  0 (REFERENCE): pin sits flush with the cover (neutral)
///   Level +1 (ABOVE)  : pin extends above the cover
///
/// Pins smoothly lerp toward their target level. Each simulation pattern
/// assigns one of the 3 levels per pin based on proximity to a virtual object.
/// </summary>
public class GridMovement : MonoBehaviour
{
    [Header("References")]
    public GridGenerator grid;

    [Header("Simulation Mode")]
    [Tooltip("Auto-cycle through different detection patterns")]
    public bool autoCycle = true;

    [Tooltip("Seconds per pattern before switching")]
    public float cycleInterval = 6f;

    [Tooltip("Current active pattern (0-4)")]
    public int activePattern = 0;

    [Header("Pin Response")]
    [Tooltip("How fast pins move to their target level")]
    public float pinLerpSpeed = 10f;

    [Tooltip("Whether to snap to exact 3 levels (true) or allow smooth in-between (false)")]
    public bool snapToLevels = true;

    [Header("Pattern: Moving Sphere")]
    public float sphereRadius = 0.015f;
    public float sphereSpeed = 1.5f;

    [Header("Pattern: Hand / Fingers")]
    public int fingerCount = 5;
    public float fingerRadius = 0.006f;

    [Header("Pattern: Ripple")]
    public float rippleSpeed = 3f;
    public float rippleFrequency = 4f;

    [Header("Pattern: Scan Line")]
    public float scanSpeed = 2f;
    public float scanWidth = 0.008f;

    [Header("Pattern: Random Pulse")]
    public float pulseInterval = 0.15f;

    // Internal
    private float[] targetTopY;    // Target absolute Y for each pin's top
    private float timeElapsed;
    private float lastCycleTime;
    private float lastPulseTime;
    private float[] pulseTimers;
    private Vector2[] fingerPositions;
    private float gridWidth;
    private float gridDepth;

    // Shorthand for the 3 levels
    private float lvBelow;  // level -1
    private float lvMid;    // level  0 (reference)
    private float lvAbove;  // level +1

    void Start()
    {
        if (grid == null) grid = GetComponent<GridGenerator>();
        Invoke(nameof(Initialize), 0.15f);
    }

    void Initialize()
    {
        if (grid == null || grid.gridPins == null) return;

        lvBelow = grid.pinLevelHeights[0];
        lvMid   = grid.pinLevelHeights[1];
        lvAbove = grid.pinLevelHeights[2];

        int count = grid.gridPins.Length;
        targetTopY = new float[count];
        pulseTimers = new float[count];

        for (int i = 0; i < count; i++)
        {
            targetTopY[i] = lvMid; // Start at reference
            pulseTimers[i] = 0f;
        }

        gridWidth = grid.columns * grid.pinSize + (grid.columns - 1) * grid.pinGap;
        gridDepth = grid.rows * grid.pinSize + (grid.rows - 1) * grid.pinGap;

        fingerPositions = new Vector2[fingerCount];
        for (int i = 0; i < fingerCount; i++)
        {
            fingerPositions[i] = new Vector2(
                Random.Range(-gridWidth / 2f, gridWidth / 2f),
                Random.Range(-gridDepth / 2f, gridDepth / 2f));
        }

        timeElapsed = 0f;
        lastCycleTime = 0f;
        lastPulseTime = 0f;
    }

    void Update()
    {
        if (grid == null || grid.gridPins == null || targetTopY == null) return;

        timeElapsed += Time.deltaTime;

        // Auto-cycle
        if (autoCycle && timeElapsed - lastCycleTime > cycleInterval)
        {
            activePattern = (activePattern + 1) % 5;
            lastCycleTime = timeElapsed;
        }

        // Compute raw target per pattern
        switch (activePattern)
        {
            case 0: PatternMovingSphere(); break;
            case 1: PatternHand(); break;
            case 2: PatternRipple(); break;
            case 3: PatternScanLine(); break;
            case 4: PatternRandomPulse(); break;
        }

        // Snap and apply
        float floorY = 0.0005f;
        for (int i = 0; i < grid.gridPins.Length; i++)
        {
            float target = targetTopY[i];

            // Snap to nearest of the 3 levels if enabled
            if (snapToLevels)
                target = grid.SnapToLevel(target);

            // Current pin top Y = floorY + pinCurrentHeight
            float currentTopY = floorY + grid.pinCurrentHeights[i];
            float newTopY = Mathf.Lerp(currentTopY, target, Time.deltaTime * pinLerpSpeed);
            grid.SetPinHeight(i, newTopY);
        }
    }


    private void PatternMovingSphere()
    {
        float t = timeElapsed * sphereSpeed;
        float sx = Mathf.Sin(t) * gridWidth * 0.35f;
        float sz = Mathf.Sin(t * 2f) * gridDepth * 0.3f;
        Vector2 spherePos = new Vector2(sx, sz);

        for (int i = 0; i < grid.gridPins.Length; i++)
        {
            Vector3 bp = grid.pinBasePositions[i];
            float dist = Vector2.Distance(new Vector2(bp.x, bp.z), spherePos);

            if (dist < sphereRadius * 0.5f)
                targetTopY[i] = lvAbove;                // directly under → UP
            else if (dist < sphereRadius)
                targetTopY[i] = lvMid;                  // edge → REFERENCE
            else
                targetTopY[i] = lvBelow;                // far away → BELOW
        }
    }

   
    private void PatternHand()
    {
        float drift = Time.deltaTime * 0.005f;
        for (int f = 0; f < fingerCount; f++)
        {
            fingerPositions[f] += new Vector2(
                Mathf.Sin(timeElapsed * 0.8f + f * 1.2f) * drift,
                Mathf.Cos(timeElapsed * 0.6f + f * 0.9f) * drift);
            fingerPositions[f].x = Mathf.Clamp(fingerPositions[f].x, -gridWidth / 2f, gridWidth / 2f);
            fingerPositions[f].y = Mathf.Clamp(fingerPositions[f].y, -gridDepth / 2f, gridDepth / 2f);
        }

        for (int i = 0; i < grid.gridPins.Length; i++)
        {
            Vector3 bp = grid.pinBasePositions[i];
            Vector2 pinPos = new Vector2(bp.x, bp.z);

            float closestDist = float.MaxValue;
            for (int f = 0; f < fingerCount; f++)
            {
                float d = Vector2.Distance(pinPos, fingerPositions[f]);
                if (d < closestDist) closestDist = d;
            }

            if (closestDist < fingerRadius * 0.5f)
                targetTopY[i] = lvAbove;
            else if (closestDist < fingerRadius)
                targetTopY[i] = lvMid;
            else
                targetTopY[i] = lvBelow;
        }
    }

  
    private void PatternRipple()
    {
        for (int i = 0; i < grid.gridPins.Length; i++)
        {
            Vector3 bp = grid.pinBasePositions[i];
            float dist = Mathf.Sqrt(bp.x * bp.x + bp.z * bp.z);
            float wave = Mathf.Sin(dist * rippleFrequency * 100f - timeElapsed * rippleSpeed);

            if (wave > 0.33f)
                targetTopY[i] = lvAbove;
            else if (wave > -0.33f)
                targetTopY[i] = lvMid;
            else
                targetTopY[i] = lvBelow;
        }
    }

    
    private void PatternScanLine()
    {
        float scanX = Mathf.Sin(timeElapsed * scanSpeed) * gridWidth * 0.5f;

        for (int i = 0; i < grid.gridPins.Length; i++)
        {
            Vector3 bp = grid.pinBasePositions[i];
            float distToLine = Mathf.Abs(bp.x - scanX);

            if (distToLine < scanWidth * 0.5f)
                targetTopY[i] = lvAbove;                 // in the scan line
            else if (bp.x < scanX)
                targetTopY[i] = lvBelow;                 // already scanned → retract
            else
                targetTopY[i] = lvMid;                   // not yet scanned → reference
        }
    }

    
    private void PatternRandomPulse()
    {
        if (timeElapsed - lastPulseTime > pulseInterval)
        {
            int count = Random.Range(3, 10);
            for (int j = 0; j < count; j++)
            {
                int idx = Random.Range(0, grid.gridPins.Length);
                pulseTimers[idx] = 1f;
            }
            lastPulseTime = timeElapsed;
        }

        for (int i = 0; i < grid.gridPins.Length; i++)
        {
            if (pulseTimers[i] > 0.6f)
                targetTopY[i] = lvAbove;        // rising phase
            else if (pulseTimers[i] > 0.2f)
                targetTopY[i] = lvMid;          // passing through reference
            else if (pulseTimers[i] > 0f)
                targetTopY[i] = lvBelow;        // sinking below
            else
                targetTopY[i] = lvMid;          // resting at reference

            if (pulseTimers[i] > 0f)
                pulseTimers[i] -= Time.deltaTime * 1.5f;
        }
    }
}
