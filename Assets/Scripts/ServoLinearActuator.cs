using UnityEngine;

/// <summary>
/// Visualises a 3×3 servo-driven linear actuator — OUTPUT VIEW ONLY.
/// Shows the rods and pins moving up/down (linear output) driven by
/// crank-slider math from servo angles. 4 auto-cycling patterns.
/// </summary>
public class ServoLinearActuator : MonoBehaviour
{
    [Header("Grid Layout")]
    public int columns = 3;
    public int rows = 3;
    [Tooltip("Center-to-center spacing between units (meters)")]
    public float cellSpacing = 0.032f;

    [Header("Servo Arm (hidden, used for crank-slider math)")]
    public float armLength = 0.010f;

    [Header("Connecting Rod")]
    public float rodLength   = 0.015f;
    public float rodDiameter = 0.002f;

    [Header("Output Pin / Slider")]
    public float pinLength   = 0.012f;
    public float pinDiameter = 0.004f;

    [Header("Guide Rail")]
    public bool showGuideRail = true;
    public float guideHeight  = 0.030f;
    public float guideWidth   = 0.006f;

    [Header("Servo Angle")]
    public float minAngle = -70f;
    public float maxAngle = 70f;

    [Header("Servo Response")]
    public float servoSpeed = 8f;

    [Header("Simulation Mode")]
    public bool autoCycle = true;
    public float cycleInterval = 5f;
    [Tooltip("Active pattern (0-3)")]
    public int activePattern = 0;

    [Header("Colors")]
    public Color bodyColor  = new Color(0.15f, 0.40f, 0.70f);
    public Color rodColor   = new Color(0.85f, 0.45f, 0.10f);
    public Color pinColor   = new Color(0.20f, 0.90f, 0.20f);
    public Color jointColor = new Color(0.95f, 0.20f, 0.20f);
    public Color guideColor = new Color(0.6f, 0.8f, 1.0f, 0.15f);
    public Color baseColor  = new Color(0.22f, 0.20f, 0.18f);

    [Header("Side-by-Side Layout")]
    [Tooltip("Offset applied to content root for side-by-side display")]
    public Vector3 positionOffset = new Vector3(0.025f, 0f, 0f);

    // ── Per-unit data ──
    private struct OutputUnit
    {
        public Transform rod;
        public Transform pin;
        public Transform pinCap;
        public Transform jointTop;
        public Transform jointBot;
        public float shaftY;
    }

    private float[] currentAngles;
    private float[] targetAngles;
    private int[] gridRows;
    private int[] gridCols;
    private OutputUnit[] outUnits;

    private int totalUnits;
    private float timeElapsed;
    private float lastCycleTime;

    // Pattern 0 state
    private int seqIndex;
    private float seqTimer;

    private Material matRod, matPin, matJoint;

    // Default shaft height (SG90 procedural dimensions)
    private float defaultShaftY;

    // ═══════════════════════════════════════════════
    //  BUILD
    // ═══════════════════════════════════════════════

    void Start()
    {
        matRod   = MakeMat(rodColor, 0.6f, 0.3f);
        matPin   = MakeMat(pinColor, 0.7f, 0.1f);
        matJoint = MakeMat(jointColor, 0.5f, 0.2f);

        // SG90 body height + shaft nub
        defaultShaftY = 0.0225f + 0.004f;

        totalUnits = columns * rows;
        currentAngles = new float[totalUnits];
        targetAngles  = new float[totalUnits];
        gridRows = new int[totalUnits];
        gridCols = new int[totalUnits];
        outUnits = new OutputUnit[totalUnits];

        for (int i = 0; i < totalUnits; i++)
        {
            currentAngles[i] = 0f;
            targetAngles[i]  = 0f;
        }

        BuildOutputGrid();

        timeElapsed = 0f;
        lastCycleTime = 0f;
        seqIndex = 0;
        seqTimer = 0f;
    }

    void BuildOutputGrid()
    {
        // Content root for side-by-side offset
        GameObject contentRoot = new GameObject("OutputContent");
        contentRoot.transform.SetParent(transform);
        contentRoot.transform.localPosition = positionOffset;
        Transform root = contentRoot.transform;

        float gridW = (columns - 1) * cellSpacing;
        float gridD = (rows - 1) * cellSpacing;
        float platW = gridW + cellSpacing * 1.2f;
        float platD = gridD + cellSpacing * 1.2f;
        float platH = 0.003f;

        // Platform
        GameObject platform = Prim("Platform", PrimitiveType.Cube, root);
        platform.transform.localScale    = new Vector3(platW, platH, platD);
        platform.transform.localPosition = new Vector3(0, -platH / 2f, 0);
        platform.GetComponent<Renderer>().material = MakeMat(baseColor, 0.3f);

        // Edge trim
        AddEdgeTrim(root, platW, platD);

        // Build units
        float startX = -gridW / 2f;
        float startZ = -gridD / 2f;

        for (int r = 0; r < rows; r++)
        {
            for (int c = 0; c < columns; c++)
            {
                int idx = r * columns + c;
                gridRows[idx] = r;
                gridCols[idx] = c;
                float x = startX + c * cellSpacing;
                float z = startZ + r * cellSpacing;

                GameObject outRoot = new GameObject($"OutUnit_{r}_{c}");
                outRoot.transform.SetParent(root);
                outRoot.transform.localPosition = new Vector3(x, 0, z);
                outUnits[idx] = BuildOutputUnit(outRoot.transform, defaultShaftY);
            }
        }
    }

    OutputUnit BuildOutputUnit(Transform parent, float shaftY)
    {
        OutputUnit u = new OutputUnit();
        u.shaftY = shaftY;

        // Housing block at the bottom
        GameObject housing = Prim("Housing", PrimitiveType.Cube, parent);
        float housingH = shaftY;
        housing.transform.localScale    = new Vector3(cellSpacing * 0.5f, housingH, cellSpacing * 0.5f);
        housing.transform.localPosition = new Vector3(0, housingH / 2f, 0);
        housing.GetComponent<Renderer>().material = MakeMat(new Color(bodyColor.r, bodyColor.g, bodyColor.b, 0.4f), 0.3f, 0f, true);

        // Bottom joint
        GameObject jb = Prim("JointBot", PrimitiveType.Sphere, parent);
        jb.transform.localScale = Vector3.one * (rodDiameter * 2f);
        jb.GetComponent<Renderer>().material = matJoint;
        u.jointBot = jb.transform;

        // Rod
        GameObject rodGo = Prim("Rod", PrimitiveType.Cylinder, parent);
        rodGo.transform.localScale = new Vector3(rodDiameter, rodLength / 2f, rodDiameter);
        rodGo.GetComponent<Renderer>().material = matRod;
        u.rod = rodGo.transform;

        // Top joint
        GameObject jt = Prim("JointTop", PrimitiveType.Sphere, parent);
        jt.transform.localScale = Vector3.one * (rodDiameter * 2f);
        jt.GetComponent<Renderer>().material = matJoint;
        u.jointTop = jt.transform;

        // Output pin
        GameObject pinGo = Prim("Pin", PrimitiveType.Cylinder, parent);
        pinGo.transform.localScale = new Vector3(pinDiameter, pinLength / 2f, pinDiameter);
        pinGo.GetComponent<Renderer>().material = matPin;
        u.pin = pinGo.transform;

        // Pin cap
        GameObject cap = Prim("PinCap", PrimitiveType.Cylinder, parent);
        cap.transform.localScale = new Vector3(pinDiameter * 1.6f, 0.0008f, pinDiameter * 1.6f);
        cap.GetComponent<Renderer>().material = MakeMat(new Color(0.1f, 0.85f, 0.1f), 0.8f);
        u.pinCap = cap.transform;

        // Guide rail
        if (showGuideRail)
        {
            GameObject gr = Prim("GuideRail", PrimitiveType.Cube, parent);
            float railY = shaftY + guideHeight / 2f;
            gr.transform.localScale    = new Vector3(guideWidth, guideHeight, guideWidth);
            gr.transform.localPosition = new Vector3(0, railY, 0);
            gr.GetComponent<Renderer>().material = MakeMat(guideColor, 0.3f, 0f, true);
        }

        return u;
    }

    // ═══════════════════════════════════════════════
    //  UPDATE
    // ═══════════════════════════════════════════════

    void Update()
    {
        if (currentAngles == null) return;

        timeElapsed += Time.deltaTime;

        // Auto-cycle
        if (autoCycle && timeElapsed - lastCycleTime > cycleInterval)
        {
            activePattern = (activePattern + 1) % 4;
            lastCycleTime = timeElapsed;
            if (activePattern == 0) { seqIndex = 0; seqTimer = 0f; }
        }

        // Compute target angles
        switch (activePattern)
        {
            case 0: PatternSequentialSweep(); break;
            case 1: PatternDiagonalWave();    break;
            case 2: PatternRadialPulse();     break;
            case 3: PatternSyncSweep();       break;
        }

        // Apply
        for (int i = 0; i < totalUnits; i++)
        {
            currentAngles[i] = Mathf.Lerp(currentAngles[i], targetAngles[i], Time.deltaTime * servoSpeed);
            UpdateOutputView(i);
        }
    }

    void UpdateOutputView(int i)
    {
        OutputUnit u = outUnits[i];
        if (u.pin == null) return;

        float rad  = currentAngles[i] * Mathf.Deg2Rad;
        float cosA = Mathf.Cos(rad);
        float sinA = Mathf.Sin(rad);

        // Crank-slider formula
        float r  = armLength;
        float L  = rodLength;
        float sq = L * L - r * r * cosA * cosA;
        if (sq < 0f) sq = 0f;
        float pinBottomY = u.shaftY + r * sinA + Mathf.Sqrt(sq);

        // Rod
        float rodBot = u.shaftY;
        float rodTop = pinBottomY;
        float rodMidY = (rodBot + rodTop) / 2f;
        float rodH = rodTop - rodBot;
        u.rod.localPosition = new Vector3(0, rodMidY, 0);
        u.rod.localScale    = new Vector3(rodDiameter, Mathf.Max(rodH / 2f, 0.0005f), rodDiameter);
        u.rod.localRotation = Quaternion.identity;

        // Joints
        u.jointBot.localPosition = new Vector3(0, rodBot, 0);
        u.jointTop.localPosition = new Vector3(0, rodTop, 0);

        // Pin
        u.pin.localPosition = new Vector3(0, pinBottomY + pinLength / 2f, 0);

        // Cap
        if (u.pinCap != null)
            u.pinCap.localPosition = new Vector3(0, pinBottomY + pinLength + 0.0004f, 0);
    }

    // ═══════════════════════════════════════════════
    //  PATTERNS
    // ═══════════════════════════════════════════════

    void PatternSequentialSweep()
    {
        float sweepDuration = cycleInterval / (float)totalUnits;
        seqTimer += Time.deltaTime;

        if (seqTimer > sweepDuration)
        {
            seqTimer -= sweepDuration;
            seqIndex = (seqIndex + 1) % totalUnits;
        }

        float phase = seqTimer / sweepDuration;

        for (int i = 0; i < totalUnits; i++)
        {
            if (i == seqIndex)
            {
                if (phase < 0.33f)
                    targetAngles[i] = Mathf.Lerp(0, maxAngle, phase / 0.33f);
                else if (phase < 0.67f)
                    targetAngles[i] = Mathf.Lerp(maxAngle, minAngle, (phase - 0.33f) / 0.34f);
                else
                    targetAngles[i] = Mathf.Lerp(minAngle, 0, (phase - 0.67f) / 0.33f);
            }
            else
            {
                targetAngles[i] = 0f;
            }
        }
    }

    void PatternDiagonalWave()
    {
        for (int i = 0; i < totalUnits; i++)
        {
            float diag = gridRows[i] + gridCols[i];
            float wave = Mathf.Sin(timeElapsed * 3f - diag * 2f);
            targetAngles[i] = Mathf.Lerp(minAngle, maxAngle, (wave + 1f) / 2f);
        }
    }

    void PatternRadialPulse()
    {
        float centerR = (rows - 1) / 2f;
        float centerC = (columns - 1) / 2f;

        for (int i = 0; i < totalUnits; i++)
        {
            float dr = gridRows[i] - centerR;
            float dc = gridCols[i] - centerC;
            float dist = Mathf.Sqrt(dr * dr + dc * dc);
            float wave = Mathf.Sin(timeElapsed * 4f - dist * 3f);

            if (wave > 0.33f)
                targetAngles[i] = maxAngle;
            else if (wave > -0.33f)
                targetAngles[i] = 0f;
            else
                targetAngles[i] = minAngle;
        }
    }

    void PatternSyncSweep()
    {
        float wave = Mathf.Sin(timeElapsed * 2f);
        float angle = Mathf.Lerp(minAngle, maxAngle, (wave + 1f) / 2f);

        for (int i = 0; i < totalUnits; i++)
            targetAngles[i] = angle;
    }

    // ═══════════════════════════════════════════════
    //  HELPERS
    // ═══════════════════════════════════════════════

    void AddEdgeTrim(Transform parent, float platW, float platD)
    {
        Material trimMat = MakeMat(new Color(0.9f, 0.5f, 0.1f, 0.8f), 0.7f);
        float trimH = 0.001f;

        GameObject f = Prim("TrimF", PrimitiveType.Cube, parent);
        f.transform.localScale    = new Vector3(platW, trimH, 0.001f);
        f.transform.localPosition = new Vector3(0, 0, -platD / 2f);
        f.GetComponent<Renderer>().material = trimMat;

        GameObject b = Prim("TrimB", PrimitiveType.Cube, parent);
        b.transform.localScale    = new Vector3(platW, trimH, 0.001f);
        b.transform.localPosition = new Vector3(0, 0, platD / 2f);
        b.GetComponent<Renderer>().material = trimMat;

        GameObject l = Prim("TrimL", PrimitiveType.Cube, parent);
        l.transform.localScale    = new Vector3(0.001f, trimH, platD);
        l.transform.localPosition = new Vector3(-platW / 2f, 0, 0);
        l.GetComponent<Renderer>().material = trimMat;

        GameObject r = Prim("TrimR", PrimitiveType.Cube, parent);
        r.transform.localScale    = new Vector3(0.001f, trimH, platD);
        r.transform.localPosition = new Vector3(platW / 2f, 0, 0);
        r.GetComponent<Renderer>().material = trimMat;
    }

    GameObject Prim(string name, PrimitiveType type, Transform parent)
    {
        GameObject o = GameObject.CreatePrimitive(type);
        o.name = name;
        o.transform.SetParent(parent);
        Collider col = o.GetComponent<Collider>();
        if (col != null) Object.Destroy(col);
        return o;
    }

    Material MakeMat(Color color, float smooth = 0.5f, float metal = 0f, bool transp = false)
    {
        Shader sh = Shader.Find("Universal Render Pipeline/Lit");
        if (sh == null) sh = Shader.Find("Standard");
        Material m = new Material(sh);
        m.color = color;
        m.SetFloat("_Smoothness", smooth);
        m.SetFloat("_Metallic", metal);
        if (transp)
        {
            m.SetFloat("_Surface", 1);
            m.SetOverrideTag("RenderType", "Transparent");
            m.SetInt("_SrcBlend", (int)UnityEngine.Rendering.BlendMode.SrcAlpha);
            m.SetInt("_DstBlend", (int)UnityEngine.Rendering.BlendMode.OneMinusSrcAlpha);
            m.SetInt("_ZWrite", 0);
            m.renderQueue = 3000;
            m.EnableKeyword("_SURFACE_TYPE_TRANSPARENT");
        }
        return m;
    }

}
