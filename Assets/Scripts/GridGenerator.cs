using UnityEngine;

public class GridGenerator : MonoBehaviour
{
    [Header("Grid Pin Layout")]
    [Tooltip("Number of pin columns")]
    public int columns = 3;

    [Tooltip("Number of pin rows")]
    public int rows = 3;

    [Tooltip("Cross-section size of each pin (meters). ~8mm")]
    public float pinSize = 0.008f;

    [Tooltip("Gap between pins (meters)")]
    public float pinGap = 0.002f;

    [Header("Reference & 3 Height Levels")]
    [Tooltip("Reference position Y — the 'neutral' surface where the cover sits")]
    public float referenceY = 0.004f;

    [Tooltip("Level -1: How far below reference a pin can retract (meters)")]
    public float levelBelow = 0.002f;

    [Tooltip("Level 0: Height offset at reference (pins flush with cover) — 0 means exactly at cover surface")]
    public float levelMid = 0.0f;

    [Tooltip("Level +1: How far above reference a pin can extend (meters)")]
    public float levelAbove = 0.004f;

    [Header("Base / Casing")]
    [Tooltip("Thickness of the device base plate")]
    public float baseThickness = 0.002f;

    [Tooltip("Height of the rim walls (from base to cover)")]
    public float rimHeight = 0.005f;

    [Tooltip("Rim wall thickness")]
    public float rimThickness = 0.0015f;

    [Tooltip("Padding inside the rim around the grid")]
    public float rimPadding = 0.002f;

    [Header("Upper Cover")]
    [Tooltip("Thickness of the upper cover plate")]
    public float coverThickness = 0.0015f;

    [Tooltip("Cover color (semi-transparent or opaque)")]
    public Color coverColor = new Color(0.14f, 0.12f, 0.1f, 0.85f);

    [Header("Side-by-Side Layout")]
    [Tooltip("Offset applied to the device root for side-by-side display")]
    public Vector3 positionOffset = new Vector3(-0.06f, 0f, 0f);

    [Header("Colors")]
    public Color pinColor = new Color(0.35f, 0.85f, 0.25f, 1f);
    public Color baseColor = new Color(0.12f, 0.1f, 0.09f, 1f);
    public Color rimColor = new Color(0.18f, 0.15f, 0.13f, 1f);
    public Color refLineColor = new Color(1f, 0.4f, 0.1f, 0.6f);

    // Public references for movement script
    [HideInInspector] public Transform[] gridPins;
    [HideInInspector] public Transform deviceTransform;
    [HideInInspector] public Vector3[] pinBasePositions;
    [HideInInspector] public float[] pinCurrentHeights;

    /// <summary>
    /// The 3 discrete target heights a pin can snap to.
    /// Level 0 = below, Level 1 = reference (mid), Level 2 = above.
    /// </summary>
    [HideInInspector] public float[] pinLevelHeights; // [0]=below, [1]=mid, [2]=above

    private Material pinMaterial;
    private Material baseMaterial;
    private Material rimMaterial;
    private Material coverMaterial;

    void Start()
    {
        GenerateGrid();
    }

    public void GenerateGrid()
    {
        // Precompute the 3 level heights (absolute Y of pin top)
        pinLevelHeights = new float[3];
        pinLevelHeights[0] = referenceY - levelBelow;  // below reference
        pinLevelHeights[1] = referenceY + levelMid;     // at reference
        pinLevelHeights[2] = referenceY + levelAbove;   // above reference

        pinMaterial = CreateMaterial(pinColor, 0.7f, 0.1f);
        baseMaterial = CreateMaterial(baseColor, 0.3f, 0.2f);
        rimMaterial = CreateMaterial(rimColor, 0.4f, 0.15f);
        coverMaterial = CreateMaterial(coverColor, 0.5f, 0.1f, coverColor.a < 1f);

        float gridWidth = columns * pinSize + (columns - 1) * pinGap;
        float gridDepth = rows * pinSize + (rows - 1) * pinGap;
        float deviceWidth = gridWidth + rimPadding * 2 + rimThickness * 2;
        float deviceDepth = gridDepth + rimPadding * 2 + rimThickness * 2;

        // Device root
        GameObject device = new GameObject("GridDevice");
        device.transform.SetParent(transform);
        device.transform.localPosition = positionOffset;
        deviceTransform = device.transform;

        // === BOTTOM BASE ===
        GameObject basePlate = MakePrimitive("Base", PrimitiveType.Cube, device.transform);
        basePlate.transform.localScale = new Vector3(deviceWidth, baseThickness, deviceDepth);
        basePlate.transform.localPosition = new Vector3(0, -baseThickness / 2f, 0);
        basePlate.GetComponent<Renderer>().material = baseMaterial;

        // === RIM WALLS ===
        MakeRimWall("RimFront", device.transform,
            new Vector3(0, rimHeight / 2f, -deviceDepth / 2f + rimThickness / 2f),
            new Vector3(deviceWidth, rimHeight, rimThickness));
        MakeRimWall("RimBack", device.transform,
            new Vector3(0, rimHeight / 2f, deviceDepth / 2f - rimThickness / 2f),
            new Vector3(deviceWidth, rimHeight, rimThickness));
        MakeRimWall("RimLeft", device.transform,
            new Vector3(-deviceWidth / 2f + rimThickness / 2f, rimHeight / 2f, 0),
            new Vector3(rimThickness, rimHeight, deviceDepth - rimThickness * 2f));
        MakeRimWall("RimRight", device.transform,
            new Vector3(deviceWidth / 2f - rimThickness / 2f, rimHeight / 2f, 0),
            new Vector3(rimThickness, rimHeight, deviceDepth - rimThickness * 2f));

        // === INNER FLOOR ===
        GameObject innerFloor = MakePrimitive("InnerFloor", PrimitiveType.Cube, device.transform);
        float innerW = deviceWidth - rimThickness * 2f;
        float innerD = deviceDepth - rimThickness * 2f;
        innerFloor.transform.localScale = new Vector3(innerW, 0.0005f, innerD);
        innerFloor.transform.localPosition = new Vector3(0, 0.00025f, 0);
        innerFloor.GetComponent<Renderer>().material = CreateMaterial(
            new Color(baseColor.r * 1.3f, baseColor.g * 1.3f, baseColor.b * 1.3f), 0.2f, 0.05f);

        // === UPPER COVER (with holes implied — solid plate at reference height) ===
        // The cover sits at referenceY. Pins poke through above it or hide below it.
        float coverY = referenceY;
        GameObject cover = MakePrimitive("UpperCover", PrimitiveType.Cube, device.transform);
        cover.transform.localScale = new Vector3(deviceWidth, coverThickness, deviceDepth);
        cover.transform.localPosition = new Vector3(0, coverY, 0);
        cover.GetComponent<Renderer>().material = coverMaterial;

        // === REFERENCE LINE INDICATOR (thin colored strip around cover edge) ===
        Material refMat = CreateMaterial(refLineColor, 0.8f, 0f);
        float lineThick = 0.0003f;

        GameObject refFront = MakePrimitive("RefLineFront", PrimitiveType.Cube, device.transform);
        refFront.transform.localScale = new Vector3(deviceWidth + 0.001f, lineThick, lineThick);
        refFront.transform.localPosition = new Vector3(0, coverY, -deviceDepth / 2f - lineThick);
        refFront.GetComponent<Renderer>().material = refMat;

        GameObject refBack = MakePrimitive("RefLineBack", PrimitiveType.Cube, device.transform);
        refBack.transform.localScale = new Vector3(deviceWidth + 0.001f, lineThick, lineThick);
        refBack.transform.localPosition = new Vector3(0, coverY, deviceDepth / 2f + lineThick);
        refBack.GetComponent<Renderer>().material = refMat;

        GameObject refLeft = MakePrimitive("RefLineLeft", PrimitiveType.Cube, device.transform);
        refLeft.transform.localScale = new Vector3(lineThick, lineThick, deviceDepth + 0.001f);
        refLeft.transform.localPosition = new Vector3(-deviceWidth / 2f - lineThick, coverY, 0);
        refLeft.GetComponent<Renderer>().material = refMat;

        GameObject refRight = MakePrimitive("RefLineRight", PrimitiveType.Cube, device.transform);
        refRight.transform.localScale = new Vector3(lineThick, lineThick, deviceDepth + 0.001f);
        refRight.transform.localPosition = new Vector3(deviceWidth / 2f + lineThick, coverY, 0);
        refRight.GetComponent<Renderer>().material = refMat;

        // === GRID PINS ===
        int totalPins = columns * rows;
        gridPins = new Transform[totalPins];
        pinBasePositions = new Vector3[totalPins];
        pinCurrentHeights = new float[totalPins];

        float startX = -(gridWidth / 2f) + pinSize / 2f;
        float startZ = -(gridDepth / 2f) + pinSize / 2f;
        float floorY = 0.0005f;

        for (int r = 0; r < rows; r++)
        {
            for (int c = 0; c < columns; c++)
            {
                int idx = r * columns + c;
                float x = startX + c * (pinSize + pinGap);
                float z = startZ + r * (pinSize + pinGap);

                GameObject pin = MakePrimitive($"Pin_{r}_{c}", PrimitiveType.Cube, device.transform);

                // Start at reference (mid level)
                float pinTopY = pinLevelHeights[1];
                float pinH = pinTopY - floorY;
                pin.transform.localScale = new Vector3(pinSize, pinH, pinSize);
                pin.transform.localPosition = new Vector3(x, floorY + pinH / 2f, z);

                float v = Random.Range(-0.04f, 0.04f);
                Color c1 = new Color(pinColor.r + v, pinColor.g + v * 0.5f, pinColor.b + v);
                pin.GetComponent<Renderer>().material = CreateMaterial(c1, 0.65f, 0.08f);

                gridPins[idx] = pin.transform;
                pinBasePositions[idx] = new Vector3(x, floorY, z);
                pinCurrentHeights[idx] = pinH;
            }
        }

        // === CORNER ACCENTS ===
        float cs = rimThickness * 2f;
        float ch = rimHeight + 0.001f;
        Vector3[] corners = {
            new Vector3(-deviceWidth/2f + cs/2f, ch/2f, -deviceDepth/2f + cs/2f),
            new Vector3( deviceWidth/2f - cs/2f, ch/2f, -deviceDepth/2f + cs/2f),
            new Vector3(-deviceWidth/2f + cs/2f, ch/2f,  deviceDepth/2f - cs/2f),
            new Vector3( deviceWidth/2f - cs/2f, ch/2f,  deviceDepth/2f - cs/2f),
        };
        for (int i = 0; i < 4; i++)
        {
            GameObject corner = MakePrimitive($"Corner_{i}", PrimitiveType.Cube, device.transform);
            corner.transform.localScale = new Vector3(cs, ch, cs);
            corner.transform.localPosition = corners[i];
            corner.GetComponent<Renderer>().material = rimMaterial;
        }
    }

    
    public void SetPinHeight(int index, float targetTopY)
    {
        if (gridPins == null || index < 0 || index >= gridPins.Length) return;

        // Clamp: pin top can't go below floor, and can't exceed level above + margin
        float floorY = pinBasePositions[index].y;
        float minTop = floorY + 0.001f; // at least 1mm tall
        float maxTop = pinLevelHeights[2] + levelAbove * 0.2f;
        targetTopY = Mathf.Clamp(targetTopY, minTop, maxTop);

        float pinH = targetTopY - floorY;
        pinCurrentHeights[index] = pinH;

        Transform pin = gridPins[index];
        Vector3 basePos = pinBasePositions[index];
        pin.localScale = new Vector3(pinSize, pinH, pinSize);
        pin.localPosition = new Vector3(basePos.x, floorY + pinH / 2f, basePos.z);
    }

  
    public float SnapToLevel(float targetTopY)
    {
        float bestDist = float.MaxValue;
        float bestLevel = pinLevelHeights[1];
        for (int i = 0; i < 3; i++)
        {
            float d = Mathf.Abs(targetTopY - pinLevelHeights[i]);
            if (d < bestDist) { bestDist = d; bestLevel = pinLevelHeights[i]; }
        }
        return bestLevel;
    }

    private void MakeRimWall(string name, Transform parent, Vector3 pos, Vector3 scale)
    {
        GameObject wall = MakePrimitive(name, PrimitiveType.Cube, parent);
        wall.transform.localScale = scale;
        wall.transform.localPosition = pos;
        wall.GetComponent<Renderer>().material = rimMaterial;
    }

    private GameObject MakePrimitive(string name, PrimitiveType type, Transform parent)
    {
        GameObject obj = GameObject.CreatePrimitive(type);
        obj.name = name;
        obj.transform.SetParent(parent);
        Collider col = obj.GetComponent<Collider>();
        if (col != null) Object.Destroy(col);
        return obj;
    }

    private Material CreateMaterial(Color color, float smoothness = 0.5f, float metallic = 0f, bool transparent = false)
    {
        Shader shader = Shader.Find("Universal Render Pipeline/Lit");
        if (shader == null) shader = Shader.Find("Standard");

        Material mat = new Material(shader);
        mat.color = color;
        mat.SetFloat("_Smoothness", smoothness);
        mat.SetFloat("_Metallic", metallic);

        if (transparent)
        {
            mat.SetFloat("_Surface", 1); // URP transparent
            mat.SetFloat("_Blend", 0);
            mat.SetOverrideTag("RenderType", "Transparent");
            mat.SetInt("_SrcBlend", (int)UnityEngine.Rendering.BlendMode.SrcAlpha);
            mat.SetInt("_DstBlend", (int)UnityEngine.Rendering.BlendMode.OneMinusSrcAlpha);
            mat.SetInt("_ZWrite", 0);
            mat.renderQueue = 3000;
            mat.EnableKeyword("_SURFACE_TYPE_TRANSPARENT");
        }

        return mat;
    }

}
