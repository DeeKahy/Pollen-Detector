# 5. Prepare the camera

**At the end of this step:** a bare camera board with a clean sensor, and a test picture.

The camera is used **without a lens**. The tape lies about 1 mm above the sensor, and the pollen
casts shadows straight onto it. The round metal lens mount and the tripod block must come off,
because they do not fit in the printed camera box.

> [!WARNING]
> Once the mount is off, the sensor is bare. Every speck of dust on it shows up in every picture.
> Work on a clean table, keep the sensor facing down or covered, and **never touch it**.

## Take the mount off

1. Unscrew the screws on the **back** of the board that hold the lens mount.
2. Lift the mount off. The IR filter (a small glass disc) stays in the mount. You do not need it.
3. Unscrew the tripod block from the bottom edge of the board, if it is there.
4. Keep the screws and parts in a bag, in case you want a lens later.

> [!NOTE]
> 📷 **Photos to add:** (a) the back of the camera with the mount screws marked, (b) the board with
> the mount lifted off, (c) the bare board next to the removed parts.

## Clean the sensor

Blow dust off with a lens blower. Do not use your breath (it is wet) or a cloth.

## Test picture

1. Plug the loose end of the ribbon into the camera. The contacts on the ribbon face the contacts
   in the connector. Close the latch.
2. Power on the Pi, wait a minute, and open **http://pollen-01.local:8080**.
3. In **Hardware checks**, press **Run checks**. The camera line should be OK.
4. Look at **Live preview**. Hold your hand over the sensor: the picture gets darker.

> [!NOTE]
> 📷 **Photo to add:** which way the ribbon goes into the camera's connector (blue side up or down).

> [!TIP]
> The preview without a lens is just a blur of light. That is normal. Things only get sharp
> when they lie right on top of the sensor, like the tape will.

Shut down (`sudo poweroff`) and unplug before you go on.
