using UnityEngine;

/// <summary>
/// Close-up orbiting camera designed for tiny AirPod-scale grid visualization.
/// Auto-orbits at multiple angles so pin movement is clearly visible.
/// Supports manual rotation (right-click drag) and scroll zoom.
/// </summary>
public class CameraOrbitController : MonoBehaviour
{
    [Header("Target")]
    [Tooltip("Target to orbit (auto-finds GridGenerator if null)")]
    public Transform target;

    [Header("Orbit Settings")]
    [Tooltip("Distance from the grid (meters). ~0.12 for AirPod-scale close-up")]
    public float distance = 0.12f;
    public float minDistance = 0.04f;
    public float maxDistance = 0.5f;
    public float orbitSpeed = 5f;
    public float zoomSpeed = 0.05f;

    [Header("Auto Camera Motion")]
    public bool autoRotate = true;
    public float autoRotateSpeed = 20f;

    [Tooltip("Camera smoothly shifts between high and low viewing angles")]
    public bool autoTiltCycle = true;
    public float tiltCycleSpeed = 0.3f;

    [Header("Angle Limits")]
    public float minVerticalAngle = 15f;
    public float maxVerticalAngle = 75f;

    [Header("Camera")]
    [Tooltip("Near clip plane (small for tiny objects)")]
    public float nearClip = 0.005f;
    public float fieldOfView = 40f;

    private float hAngle = 30f;
    private float vAngle = 45f;
    private Vector3 targetOffset;

    void Start()
    {
        if (target == null)
        {
            GridGenerator gen = FindObjectOfType<GridGenerator>();
            ServoLinearActuator servo = FindObjectOfType<ServoLinearActuator>();

            if (gen != null && servo != null)
            {
                // Both present — side-by-side layout
                // Create an empty pivot at the midpoint between them
                GameObject pivot = new GameObject("CameraPivot");
                float midX = (gen.positionOffset.x + servo.positionOffset.x) / 2f;
                float midY = 0.022f; // roughly between grid top and servo mid-height
                pivot.transform.position = new Vector3(midX, midY, 0f);
                target = pivot.transform;
                targetOffset = Vector3.zero;
                distance = 0.22f; // wider view to frame both grids
            }
            else if (gen != null)
            {
                target = gen.transform;
                targetOffset = new Vector3(gen.positionOffset.x, 0.01f, 0f);
                distance = 0.12f;
            }
            else if (servo != null)
            {
                target = servo.transform;
                targetOffset = new Vector3(servo.positionOffset.x, 0.018f, 0f);
                distance = 0.15f;
            }
        }

        // Set camera for close-up of tiny objects
        Camera cam = GetComponent<Camera>();
        if (cam != null)
        {
            cam.nearClipPlane = nearClip;
            cam.fieldOfView = fieldOfView;
        }

        hAngle = 30f;
        vAngle = 45f;

        if (targetOffset == Vector3.zero && target != null && target.name != "CameraPivot")
            targetOffset = new Vector3(0, 0.01f, 0);
    }

    void LateUpdate()
    {
        if (target == null) return;

        // Manual rotation with right mouse button
        if (Input.GetMouseButton(1))
        {
            hAngle += Input.GetAxis("Mouse X") * orbitSpeed;
            vAngle -= Input.GetAxis("Mouse Y") * orbitSpeed;
            vAngle = Mathf.Clamp(vAngle, minVerticalAngle, maxVerticalAngle);
            autoRotate = false;
        }

        // Resume auto-rotate on middle click
        if (Input.GetMouseButtonDown(2))
        {
            autoRotate = true;
        }

        // Auto orbit
        if (autoRotate)
        {
            hAngle += autoRotateSpeed * Time.deltaTime;
        }

        // Auto tilt cycle: smoothly vary between low and high angles
        if (autoTiltCycle)
        {
            float mid = (minVerticalAngle + maxVerticalAngle) / 2f;
            float range = (maxVerticalAngle - minVerticalAngle) / 2f;
            vAngle = mid + Mathf.Sin(Time.time * tiltCycleSpeed) * range;
        }

        // Scroll zoom
        float scroll = Input.GetAxis("Mouse ScrollWheel");
        if (scroll != 0f)
        {
            distance -= scroll * zoomSpeed;
            distance = Mathf.Clamp(distance, minDistance, maxDistance);
        }

        // Position camera
        Quaternion rot = Quaternion.Euler(vAngle, hAngle, 0);
        Vector3 offset = rot * new Vector3(0, 0, -distance);
        Vector3 lookAt = target.position + targetOffset;

        transform.position = lookAt + offset;
        transform.LookAt(lookAt);
    }
}
