# Stardew Fish Pond Expected Value Calculator

Based off decompiled source code and unpacked xnb files from `v1.6.15 (build 24356)`. I took the concept from [captncraig](https://gist.github.com/captncraig/e691aceb05e426c8aaa6c2af0c48a64f), but did my own analysis on more recent data.

Calculates expected daily sell value of fish ponds from Stardew Valley JSON data. The relevant json files are `FishPondData.json` and `Objects.json`.

Currently models:
- pond precedence
- required tags
- conditional legendary fish
- roe value
- aged roe
- artisan bonus

Assumptions:
- does not model player luck
- conditions currently only support ITEM_ID
- stack ranges are uniformly distributed

## Output

Generated reports:

- [Base fish pond values](plain_values.txt)
- [Aged roe values](aged_values.txt)
- [Artisan values](artisan_values.txt)

They are of the form

```
Sandfish (164)
	Cactus Seeds(3.5)[0]: 0.048
	Roe(2.2)[414]: 0.818
	Nothing: 0.135
	Expected Daily Value: 338.853
```

Where `Sandfish` is item `(O)164`. It generates `Roe` with an expected count of `2.2`, valuing `414` gold, this happens with probability `0.818`
