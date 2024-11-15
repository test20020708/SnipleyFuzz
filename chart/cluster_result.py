import pandas as pd
from scipy.cluster import hierarchy
import matplotlib.pyplot as plt

def main():
    featureList=[[3, 1, 5, 25, 100.0], [7, 1, 9, 63, 100.0], [7, 1, 9, 63, 100.0], [10, 2, 13, 79, 100.0], [6, 2, 9, 58, 100.0], [7, 2, 10, 63, 100.0], [6, 2, 9, 58, 100.0], [7, 2, 10, 64, 100.0]]
    df = pd.DataFrame(featureList)
    cluster = hierarchy.linkage(df, method='single', metric='euclidean')

    plt.figure(figsize=(8, 12))  # Adjust figure size to control aspect ratio

    # Plot mirrored dendrogram
    dendrogram = hierarchy.dendrogram(cluster, orientation='right')

    # Mirror the tick labels for better readability
    plt.tick_params(axis='x', rotation=0)

    plt.title('层次聚类树枝状图')
    plt.xlabel('欧式距离')
    plt.ylabel('响应索引')

    plt.show()

if __name__ == "__main__":
    main()
